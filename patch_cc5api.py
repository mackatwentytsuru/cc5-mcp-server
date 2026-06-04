import sys
Q = chr(34)
path = r"C:/Users/macka/Projects/cc5-mcp-server/cc5-plugin/cc5_api.py"
with open(path,"r",encoding="utf-8") as f:
    original = f.readlines()
keep = original[:2650]
lines = []
def a(*args): lines.append("".join(str(x) for x in args))
a("
")
a("# ---------------------------------------------------------------------------
")
a("# UR-02: Single source of truth for dispatch registry
")
a("# ---------------------------------------------------------------------------
")
a("
")
a("def build_dispatch_tables() -> tuple:
")
a("    import cc5_api as _self
")
a("
")
a("    action_map: dict = {
")
a(Q,"get_avatars",Q,": lambda p: _self.get_avatars(),
")
a(Q,"get_avatar_info",Q,": lambda p: _self.get_avatar_info(),
")
a(Q,"get_morph_catalog",Q,": lambda p: _self.get_morph_catalog(),
")
a(Q,"get_expression_info",Q,": lambda p: _self.get_expression_info(),
")
a(Q,"get_scene_objects",Q,": lambda p: _self.get_scene_objects(),
")
a(Q,"list_clothes",Q,": lambda p: _self.list_clothes(),
")
a(Q,"list_hair",Q,": lambda p: _self.list_hair(),
")
a(Q,"list_accessories",Q,": lambda p: _self.list_accessories(),
")
a(Q,"create_default_avatar",Q,": lambda p: _self.create_default_avatar(),
")
a(Q,"undo",Q,": lambda p: _self.undo(),
")
a(Q,"redo",Q,": lambda p: _self.redo(),
")
a(Q,"get_camera_info",Q,": lambda p: _self.get_camera_info(),
")
a(Q,"get_lights",Q,": lambda p: _self.get_lights(),
")
a(Q,"get_export_status",Q,": lambda p: _self.get_export_status(),
")
a(Q,"silent_trigger_dialog",Q,": lambda p: _self.silent_trigger_dialog(),
")
a(Q,"silent_finalize",Q,": lambda p: _self.silent_finalize(),
")
a(Q,"search_morphs",Q,": lambda p: _self.search_morphs(p[Q+"query"+Q], p.get(Q+"category"+Q, Q+Q)),
")
