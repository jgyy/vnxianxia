extends Node
## Music with cross-fades, pooled sound effects and a voice channel.

const MUSIC_DIR := "res://audio/music/"
const SFX_DIR := "res://audio/sfx/"
const LOOPING := ["meditate_loop", "wind_loop", "fire_loop"]

var music_volume := 0.8
var sfx_volume := 1.0
var voice_volume := 1.0
var current_music := ""

var _music: Array[AudioStreamPlayer] = []
var _active := 0
var _voice: AudioStreamPlayer
var _pool: Array[AudioStreamPlayer] = []
var _cache := {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for i in 2:
		var p := AudioStreamPlayer.new()
		p.volume_db = -80.0
		add_child(p)
		_music.append(p)
	_voice = AudioStreamPlayer.new()
	add_child(_voice)
	for i in 12:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_pool.append(p)


func _stream(path: String, loop := false) -> AudioStream:
	if _cache.has(path):
		return _cache[path]
	if not ResourceLoader.exists(path):
		return null
	var s := load(path) as AudioStream
	if s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = loop
	_cache[path] = s
	return s


## Cross-fade to a music track (ids from tools/gen_audio.py). "" fades out.
func play_music(id: String, fade := 1.5) -> void:
	if id == current_music:
		return
	current_music = id
	var old := _music[_active]
	_active = 1 - _active
	var new := _music[_active]
	var tw := create_tween().set_parallel(true)
	tw.tween_property(old, "volume_db", -80.0, fade)
	if id != "":
		var s := _stream(MUSIC_DIR + id + ".ogg", id != "victory")
		if s:
			new.stream = s
			new.volume_db = -40.0
			new.play()
			tw.tween_property(new, "volume_db", linear_to_db(music_volume), fade)
	tw.chain().tween_callback(old.stop)


func sfx(id: String, volume_db := 0.0, pitch := 1.0) -> AudioStreamPlayer:
	var s := _stream(SFX_DIR + id + ".ogg", LOOPING.has(id))
	if s == null:
		return null
	for p in _pool:
		if not p.playing:
			p.stream = s
			p.volume_db = volume_db + linear_to_db(sfx_volume)
			p.pitch_scale = pitch
			p.play()
			return p
	return null


func play_voice(path: String) -> float:
	stop_voice()
	if path.is_empty():
		return 0.0
	var s := _stream(path)
	if s == null:
		return 0.0
	_voice.stream = s
	_voice.volume_db = linear_to_db(voice_volume)
	_voice.play()
	return s.get_length()


func stop_voice() -> void:
	_voice.stop()


func voice_playing() -> bool:
	return _voice.playing
