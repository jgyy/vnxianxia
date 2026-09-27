"""Shader node layer shared by the skin, eye, mouth and hair materials.

Every material is built so that two consumers read it correctly:

* Cycles (portraits, previews) sees the full node tree: subsurface skin with a
  second, sharper "oil" specular lobe, anisotropic hair with a tinted sheen and
  back-lit translucency, a refractive-looking wet cornea.
* The glTF exporter (-> Godot) only follows the Principled BSDF and a node group
  named "glTF Material Output".  So the textures are wired in the exact patterns
  it recognises:
    - base colour: Image -> Base Color (alpha, if any, via 1 - (A < cutoff) so the
      material exports as alphaMode MASK instead of BLEND),
    - one ORM image: R = ambient occlusion (to the glTF group's Occlusion input),
      G = roughness, B = metallic -> exported as a single packed ORM texture,
    - tangent-space normal map through a Normal Map node.
  Everything Cycles-only (translucency, sheen, coat, subsurface radius) is either
  ignored by the exporter or exported as a small constant extension.

Images are created at explicit sizes (albedo, ORM and normal can differ) with the
right colour spaces (sRGB albedo, Non-Color data maps) and packed into the file.
"""
import bpy
import numpy as np

from . import tex, util

GLTF_GROUP = "glTF Material Output"


# --------------------------------------------------------------------------
# images
# --------------------------------------------------------------------------
def image(name, arr, data=False):
    """(H, W[, C]) float array in [0, 1] -> packed Blender image (row 0 = bottom)."""
    return util.image_from_array(name, np.clip(arr, 0.0, 1.0).astype(np.float32), non_color=data)


def fill_image(img, arr):
    """Overwrite the pixels of an image created earlier (same size)."""
    arr = np.clip(arr, 0.0, 1.0).astype(np.float32)
    h, w = arr.shape[:2]
    if arr.ndim == 2:
        arr = np.repeat(arr[..., None], 3, axis=2)
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), np.float32)], axis=2)
    if (img.size[0], img.size[1]) != (w, h):
        img.scale(w, h)
    img.pixels.foreach_set(np.ascontiguousarray(arr).ravel())
    img.pack()


def resize(a, size):
    """Area-average (down) or bilinear (up) resample of a (H, W[, C]) array to size x size."""
    h = a.shape[0]
    if h == size:
        return a
    if h > size and h % size == 0:
        n = h // size
        shp = (size, n, size, n) + a.shape[2:]
        return a.reshape(shp).mean(axis=(1, 3)).astype(np.float32)
    y = (np.arange(size) + 0.5) * h / size - 0.5
    y0 = np.clip(np.floor(y).astype(int), 0, h - 1)
    y1 = np.clip(y0 + 1, 0, h - 1)
    fy = np.clip(y - y0, 0, 1)
    x0, x1, fx = y0, y1, fy
    if a.ndim == 3:
        fy = fy[:, None, None]
        fxx = fx[None, :, None]
    else:
        fy = fy[:, None]
        fxx = fx[None, :]
    top = a[y0][:, x0] * (1 - fxx) + a[y0][:, x1] * fxx
    bot = a[y1][:, x0] * (1 - fxx) + a[y1][:, x1] * fxx
    return (top * (1 - fy) + bot * fy).astype(np.float32)


def orm(ao, rough, metal=None):
    """Pack occlusion / roughness / metallic into one Non-Color RGB array."""
    metal = np.zeros_like(rough) if metal is None else metal
    return np.stack([ao, rough, metal], axis=-1).astype(np.float32)


# --------------------------------------------------------------------------
# node helpers
# --------------------------------------------------------------------------
def _gltf_group():
    """Node group the glTF exporter reads Occlusion from (created once per file)."""
    grp = bpy.data.node_groups.get(GLTF_GROUP)
    if grp is None:
        grp = bpy.data.node_groups.new(GLTF_GROUP, "ShaderNodeTree")
        grp.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        grp.interface.new_socket("Thickness", in_out="INPUT", socket_type="NodeSocketFloat")
    return grp


class Tree:
    """Tiny builder around a fresh material node tree."""

    def __init__(self, name, double_sided=False):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        for n in list(self.nt.nodes):
            self.nt.nodes.remove(n)
        self.out = self.node("ShaderNodeOutputMaterial", 900, 0)
        self.bsdf = self.node("ShaderNodeBsdfPrincipled", 400, 0)
        self.mat.use_backface_culling = not double_sided
        self._y = 400

    def node(self, kind, x=0, y=0, **props):
        n = self.nt.nodes.new(kind)
        n.location = (x, y)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def tex(self, img, x=-700, closest=False):
        n = self.node("ShaderNodeTexImage", x, self._y)
        self._y -= 300
        n.image = img
        n.interpolation = "Closest" if closest else "Linear"
        return n

    def math(self, op, a, b, x=-200, y=0):
        n = self.node("ShaderNodeMath", x, y, operation=op)
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                self.link(v, n.inputs[i])
        return n.outputs[0]

    def set(self, **inputs):
        for k, v in inputs.items():
            sock = self.bsdf.inputs[k]
            if isinstance(v, bpy.types.NodeSocket):
                self.link(v, sock)
            elif isinstance(v, (tuple, list)):
                sock.default_value = tuple(v) + ((1.0,) if len(v) == 3 and len(sock.default_value) == 4 else ())
            else:
                sock.default_value = v

    def maps(self, albedo_img, orm_img=None, normal_img=None, normal_strength=1.0, alpha_cutoff=None):
        """Wire base colour / packed ORM / normal the way the glTF exporter expects."""
        a = self.tex(albedo_img)
        self.set(**{"Base Color": a.outputs["Color"]})
        if alpha_cutoff is not None:
            below = self.math("LESS_THAN", a.outputs["Alpha"], alpha_cutoff, -350, 250)
            self.set(Alpha=self.math("SUBTRACT", 1.0, below, -200, 250))
            self.mat.surface_render_method = "DITHERED"
        self.albedo_node = a
        if orm_img is not None:
            o = self.tex(orm_img)
            sep = self.node("ShaderNodeSeparateColor", -350, o.location.y)
            self.link(o.outputs["Color"], sep.inputs["Color"])
            self.set(Roughness=sep.outputs["Green"], Metallic=sep.outputs["Blue"])
            g = self.node("ShaderNodeGroup", 400, -500)
            g.node_tree = _gltf_group()
            self.link(sep.outputs["Red"], g.inputs["Occlusion"])
            self.orm_sep = sep
        if normal_img is not None and normal_strength > 0:
            n = self.tex(normal_img)
            nm = self.node("ShaderNodeNormalMap", -350, n.location.y)
            nm.inputs["Strength"].default_value = normal_strength
            self.link(n.outputs["Color"], nm.inputs["Color"])
            self.set(Normal=nm.outputs["Normal"])
            self.normal = nm.outputs["Normal"]
        return self

    def finish(self, surface=None):
        self.link(surface if surface is not None else self.bsdf.outputs["BSDF"], self.out.inputs["Surface"])
        return self.mat


def linear(hexstr, k=1.0):
    return tuple(util.srgb_to_linear(x) * k for x in tex.srgb(hexstr))


# --------------------------------------------------------------------------
# material recipes
# --------------------------------------------------------------------------
def skin_material(name, albedo_img, orm_img, normal_img, sss=1.0, oil=0.08,
                  normal_strength=1.0, radius=(1.0, 0.37, 0.19), scale=0.0042, vellus=0.12):
    """Layered skin: random-walk subsurface, textured base specular and a thin oil coat.

    radius/scale follow measured skin mean free paths (~3.7 / 1.4 / 0.7 mm red/green/blue,
    scaled down because the head is small and the texture already holds the scattering tint).
    """
    t = Tree(name)
    t.maps(albedo_img, orm_img, normal_img, normal_strength)
    t.bsdf.subsurface_method = "RANDOM_WALK_SKIN"
    t.set(**{"Subsurface Weight": sss, "Subsurface Radius": radius, "Subsurface Scale": scale,
             "IOR": 1.4, "Specular IOR Level": 0.5, "Coat Weight": oil, "Coat Roughness": 0.22,
             "Coat IOR": 1.45, "Sheen Weight": vellus, "Sheen Roughness": 0.45,
             "Sheen Tint": (1.0, 0.9, 0.85, 1.0)})
    if hasattr(t, "normal"):
        t.link(t.normal, t.bsdf.inputs["Coat Normal"])
    return t.finish()


def hair_material(name, albedo_img, orm_img, normal_img, hair_hex, cutoff=0.42, anisotropy=0.75,
                  translucency=0.22):
    """Alpha-tested, two-sided hair cards.

    Cycles: anisotropic primary specular stretched across the strands (tangent = UV u),
    a hair-coloured sheen standing in for the secondary (TRT) lobe, and a translucent
    component for back-lit edges.  glTF: MASK alpha, ORM, normal, doubleSided.
    """
    t = Tree(name, double_sided=True)
    t.maps(albedo_img, orm_img, normal_img, 0.8, alpha_cutoff=cutoff)
    tan = t.node("ShaderNodeTangent", 0, -700, direction_type="UV_MAP")
    t.set(IOR=1.55, **{"Specular IOR Level": 0.6, "Anisotropic": anisotropy, "Anisotropic Rotation": 0.0,
                       "Tangent": tan.outputs["Tangent"], "Sheen Weight": 0.35, "Sheen Roughness": 0.35,
                       "Sheen Tint": (*linear(hair_hex, 3.0), 1.0)})
    # back-lit translucency, clipped by the same alpha so the card outline stays cut out
    alpha = t.bsdf.inputs["Alpha"].links[0].from_socket
    trans = t.node("ShaderNodeBsdfTranslucent", 400, -300)
    t.link(t.albedo_node.outputs["Color"], trans.inputs["Color"])
    clear = t.node("ShaderNodeBsdfTransparent", 400, -450)
    cut = t.node("ShaderNodeMixShader", 600, -350)
    t.link(alpha, cut.inputs[0])
    t.link(clear.outputs[0], cut.inputs[1])
    t.link(trans.outputs[0], cut.inputs[2])
    mix = t.node("ShaderNodeMixShader", 750, 0)
    mix.inputs[0].default_value = translucency
    t.link(t.bsdf.outputs["BSDF"], mix.inputs[1])
    t.link(cut.outputs[0], mix.inputs[2])
    return t.finish(mix.outputs[0])


def simple_material(name, albedo_img, orm_img=None, normal_img=None, normal_strength=1.0, double_sided=False,
                    alpha_cutoff=None, sss=0.0, sss_radius=(1.0, 0.4, 0.25), sss_scale=0.002,
                    ior=1.45, spec=0.5, coat=0.0, emission_img=None, emission_strength=0.0):
    """Generic textured Principled material (teeth, tongue, eyes, lashes, scalp...)."""
    t = Tree(name, double_sided=double_sided)
    t.maps(albedo_img, orm_img, normal_img, normal_strength, alpha_cutoff=alpha_cutoff)
    t.set(IOR=ior, **{"Specular IOR Level": spec})
    if sss > 0:
        t.bsdf.subsurface_method = "RANDOM_WALK"
        t.set(**{"Subsurface Weight": sss, "Subsurface Radius": sss_radius, "Subsurface Scale": sss_scale})
    if coat > 0:
        t.set(**{"Coat Weight": coat, "Coat Roughness": 0.03, "Coat IOR": 1.376})
    if emission_img is not None:
        e = t.tex(emission_img)
        t.set(**{"Emission Color": e.outputs["Color"], "Emission Strength": emission_strength})
    return t.finish()


def film_material(name, color_hex, alpha, rough=0.03, ior=1.376):
    """Untextured transparent wet film (cornea, tear line): alpha-blended gloss.

    The base colour is near black so the film only adds its reflection; the small
    alpha keeps the darkening of what lies beneath negligible in Godot.
    """
    t = Tree(name)
    t.set(**{"Base Color": (*linear(color_hex), 1.0), "Roughness": rough, "IOR": ior,
             "Specular IOR Level": 1.0, "Alpha": alpha})
    t.mat.surface_render_method = "BLENDED"
    return t.finish()
