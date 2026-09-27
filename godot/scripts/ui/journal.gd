extends CanvasLayer
## Pause menu and quest journal (Esc / J): current quest, chronicle of
## completed quests, cultivation & inventory, settings, save and quit.

signal quit_to_title
signal closed

var open := false
var _content: RichTextLabel
var _root: Control
var _settings: VBoxContainer


func _ready() -> void:
	layer = 12
	process_mode = Node.PROCESS_MODE_ALWAYS
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.theme = UiTheme.get_theme()
	add_child(_root)
	var dim := ColorRect.new()
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0, 0, 0, 0.55)
	_root.add_child(dim)
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.position = Vector2(-470, -290)
	panel.custom_minimum_size = Vector2(940, 580)
	panel.add_theme_stylebox_override("panel", UiTheme.panel(Color(0.05, 0.055, 0.08, 0.95), UiTheme.GOLD, 8, 2))
	_root.add_child(panel)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 20)
	panel.add_child(hb)
	var menu := VBoxContainer.new()
	menu.custom_minimum_size.x = 200
	menu.add_theme_constant_override("separation", 8)
	hb.add_child(menu)
	var head := UiTheme.label("Journal", 30, UiTheme.GOLD, 5)
	menu.add_child(head)
	for pair in [["Current Quest", _show_quest], ["Story So Far", _show_story], ["Chronicle", _show_chronicle],
			["Cultivation", _show_cultivation], ["Settings", _show_settings], ["Save Game", _save],
			["Resume", close], ["Quit to Title", _quit]]:
		var b := Button.new()
		b.text = pair[0]
		b.pressed.connect(pair[1])
		b.pressed.connect(func(): Audio.sfx("ui_click", -6.0))
		menu.add_child(b)
	var right := VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hb.add_child(right)
	_content = RichTextLabel.new()
	_content.bbcode_enabled = true
	_content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_content.add_theme_font_size_override("normal_font_size", 18)
	_content.add_theme_font_size_override("bold_font_size", 22)
	right.add_child(_content)
	_settings = VBoxContainer.new()
	_settings.visible = false
	right.add_child(_settings)
	for pair in [["Music", "music_volume"], ["Effects", "sfx_volume"], ["Voices", "voice_volume"]]:
		var row := HBoxContainer.new()
		var l := UiTheme.label(pair[0], 18)
		l.custom_minimum_size.x = 120
		row.add_child(l)
		var s := HSlider.new()
		s.min_value = 0.0
		s.max_value = 1.0
		s.step = 0.05
		s.value = Audio.get(pair[1])
		s.custom_minimum_size.x = 360
		var key: String = pair[1]
		s.value_changed.connect(func(v): Audio.set(key, v))
		row.add_child(s)
		_settings.add_child(row)
	visible = false


func toggle(page := "quest") -> void:
	if open:
		close()
	else:
		show_page(page)


func show_page(page := "quest") -> void:
	open = true
	visible = true
	get_tree().paused = true
	Audio.sfx("ui_open", -6.0)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	match page:
		"chronicle":
			_show_chronicle()
		"story":
			_show_story()
		_:
			_show_quest()


func close() -> void:
	if not open:
		return
	open = false
	visible = false
	get_tree().paused = false
	Audio.sfx("ui_close", -6.0)
	closed.emit()


func _unhandled_input(event: InputEvent) -> void:
	if open and (event.is_action_pressed("pause") or event.is_action_pressed("journal")):
		close()
		get_viewport().set_input_as_handled()


func _page(text: String) -> void:
	_settings.visible = false
	_content.visible = true
	_content.text = text
	_content.scroll_to_line(0)


func _show_quest() -> void:
	var q := Game.quest()
	if q.is_empty():
		_page("[b]The saga is complete.[/b]\n\nYou have ascended. The realms are yours to wander.")
		return
	var t := "[color=#b8ad96]%s  —  %s[/color]\n[b][color=#dcb86b]%d. %s[/color][/b]\n\n%s\n\n" % [
		Story.volume_label(int(q.get("volume", 1))), Story.chapter_label(int(q.chapter)), int(q.number), q.title,
		Story.fill(q.summary)]
	var objs: Array = q.objectives
	for i in objs.size():
		var o: Dictionary = objs[i]
		var mark := "[color=#73e6c7]+[/color]" if i < Game.objective_index else ("»" if i == Game.objective_index else "·")
		var where := "" if o.map == Game.map_id else "  [color=#8f8a80](%s)[/color]" % Story.map_name(o.map)
		var col := "#8f8a80" if i < Game.objective_index else ("#f5eedb" if i == Game.objective_index else "#b8ad96")
		t += "%s [color=%s]%s[/color]%s\n" % [mark, col, Story.fill(o.text), where]
	var r: Dictionary = q.rewards
	t += "\n[color=#b8ad96]Rewards:[/color] %d cultivation" % int(r.get("xp", 0))
	for item in r.get("items", {}):
		t += " · %s ×%d" % [Story.item_name(item), int(r.items[item])]
	if r.get("realm"):
		t += " · [color=#dcb86b]Breakthrough: %s[/color]" % r.realm
	elif r.get("stage") != null:
		t += " · [color=#73e6c7]%s[/color]" % Story.realm_label(int(q.tier), int(r.stage))
	for o in objs:
		if o.type == "tribulation":
			t += "\n[color=#9fb4ff]A heavenly tribulation of %d bolts awaits.[/color]" % int(o.bolts)
	_page(t)


## The narrative recap: premise, then every volume and chapter reached. Quest
## summaries are listed for the current chapter only, so the page stays short
## (and fast) even 900 quests in.
func _show_story() -> void:
	var t := "[b][color=#dcb86b]%s[/color][/b]\n\n[i]%s[/i]\n" % [Story.title, Story.premise]
	var cur := Game.quest()
	var cur_ch := int(cur.chapter) if not cur.is_empty() else Story.chapters.size() + 1
	for v in Story.volumes:
		if int(v.first) > Game.quest_index:
			break
		t += "\n\n[b][color=#dcb86b]%s[/color][/b]  [color=#b8ad96]%s[/color]\n[i]%s[/i]\n" % [
			Story.volume_label(int(v.number)), v.subtitle, Story.fill(v.summary)]
		for n in v.chapters:
			var c := Story.chapter(int(n))
			var first := int(c.first)
			if first > Game.quest_index:
				break
			t += "\n[b]Chapter %d · %s[/b]\n%s\n" % [int(n), c.title, Story.fill(c.summary)]
			if int(n) == cur_ch or (int(n) == Story.chapters.size() and Game.finished()):
				for i in range(first, mini(first + 10, Game.quest_index)):
					var q := Story.quest(i)
					t += "[color=#b8ad96]   %d. %s[/color] — %s\n" % [int(q.number), q.title, Story.fill(q.summary)]
	t += _threads_text()
	_page(t)


## Recurring threads (the traitor, the pendant, the Patriarch's Ladder...):
## every beat reached so far, oldest first, so the saga reads like one story
## even when its 1000 quests are played one at a time.
func _threads_text() -> String:
	var reached: Array = Story.threads_so_far(Game.quest_index)
	if reached.is_empty():
		return ""
	var t := "\n\n[b][color=#dcb86b]Threads of the story[/color][/b]\n"
	for th in reached:
		var mark := "[color=#73e6c7]—[/color]" if th.done else "[color=#dcb86b]…[/color]"
		t += "\n%s [b]%s[/b]\n" % [mark, th.title]
		for beat in (th.beats as Array):
			t += "   %s\n" % beat
	return t


## Every quest reached in the current volume; earlier volumes are folded into
## their chapter titles, later ones into a single line each.
func _show_chronicle() -> void:
	var t := "[b][color=#dcb86b]Chronicle[/color][/b]   [color=#b8ad96]%d / %d quests[/color]\n" % [
		mini(Game.quest_index, Story.quests.size()), Story.quests.size()]
	var cur := Game.quest()
	var cur_vol := int(cur.get("volume", Story.volumes.size())) if not cur.is_empty() else Story.volumes.size()
	for v in Story.volumes:
		var vn := int(v.number)
		if int(v.first) > Game.quest_index:
			t += "\n[color=#6f6a60]%s · ???[/color]" % ("Volume " + Story.roman(vn))
			continue
		t += "\n\n[b][color=#dcb86b]%s[/color][/b]\n" % Story.volume_label(vn)
		for n in v.chapters:
			var c := Story.chapter(int(n))
			var first := int(c.first)
			if first > Game.quest_index:
				t += "[color=#6f6a60]   Chapter %d · ???[/color]\n" % int(n)
				continue
			var done_ch := first + 10 <= Game.quest_index
			t += "   %s [b]Chapter %d · %s[/b]\n" % ["[color=#73e6c7]+[/color]" if done_ch else "»", int(n), c.title]
			if vn != cur_vol or done_ch:
				continue
			for i in range(first, mini(first + 10, Game.quest_index + 1)):
				var q := Story.quest(i)
				var done := i < Game.quest_index
				t += "        %s %d. %s\n" % ["[color=#73e6c7]+[/color]" if done else "»", int(q.number), q.title]
	_page(t)


func _show_cultivation() -> void:
	var t := "[b][color=#dcb86b]%s[/color][/b]\nCultivation %d\n\nVitality %d · Qi %d · Palm strike %d · Qi blast %d\n\n" % [
		Game.realm_label(), Game.xp, int(Game.max_hp()), int(Game.max_qi()),
		int(Game.strike_damage()), int(Game.blast_damage())]
	var realms: Array = Story.world.realms
	for i in realms.size():
		var mark := "[color=#73e6c7]+[/color]" if i < Game.realm else ("»" if i == Game.realm else "[color=#6f6a60]·[/color]")
		var name: String = realms[i] if i <= Game.realm else "[color=#6f6a60]%s[/color]" % realms[i]
		if i == Game.realm and Game.stage > 0:
			# the ten minor stages of the current realm
			var pips := ""
			for s in range(1, 11):
				pips += "[color=#73e6c7]●[/color]" if s <= Game.stage else "[color=#6f6a60]○[/color]"
			name += "   %s  [color=#b8ad96]%s[/color]" % [pips, Story.stage_name(Game.realm, Game.stage)]
		t += "%s %s\n" % [mark, name]
	t += _alignment_text()
	t += "\n[b]Inventory[/b]\n"
	if Game.inventory.is_empty():
		t += "[color=#8f8a80]Empty[/color]"
	for item in Game.inventory:
		t += "%s ×%d\n" % [Story.item_name(item), int(Game.inventory[item])]
	_page(t)


## The nine alignments as a grid, the player's highlighted, with both axes.
func _alignment_text() -> String:
	var t := "\n[b]Dao Heart: [color=#dcb86b]%s[/color][/b]\n" % Game.alignment_name()
	t += "[color=#b8ad96]Bearing %+d (disciplined 25+, free-wandering -25-)  ·  Dao %+d (righteous 25+, demonic -25-)[/color]\n" % [Game.law, Game.good]
	var mine := Game.alignment()
	for a in Game.ALIGN_LAW:
		var row := "   "
		for m in Game.ALIGN_MORAL:
			var id: String = a + "_" + m
			var label := Story.alignment_name(id)
			if id == mine:
				row += "[color=#dcb86b][b]» %s «[/b][/color]   " % label
			else:
				row += "[color=#6f6a60]%s[/color]   " % label
		t += row + "\n"
	var flags: Array = Game.flags.keys()
	if not flags.is_empty():
		t += "[color=#8f8a80]Remembered: %s[/color]\n" % ", ".join(flags.map(func(f): return (f as String).replace("_", " ")))
	return t


func _show_settings() -> void:
	_content.visible = false
	_settings.visible = true


func _save() -> void:
	Game.save()
	_page("[b]Progress saved.[/b]\n\nThe sect's record keeper nods and dips the brush.")


func _quit() -> void:
	Game.save()
	close()
	quit_to_title.emit()
