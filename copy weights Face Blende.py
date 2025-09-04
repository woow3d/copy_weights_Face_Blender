import bpy
import bmesh

def copy_weights_from_active_face(use_average=True, only_nonzero_groups=False):
    obj = bpy.context.object
    if not obj or obj.type != 'MESH':
        print("Error: Select a Mesh object.")
        return False

    if bpy.context.mode != 'EDIT_MESH':
        print("Error: Must be in Edit Mode (faces selected).")
        return False

    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # Find the active/reference face from select history (most reliable)
    active_face = None
    try:
        for elem in reversed(bm.select_history):
            # check if this history element is a face and selected
            if isinstance(elem, bmesh.types.BMFace) and elem.select:
                active_face = elem
                break
    except Exception:
        active_face = None

    # fallback: try bm.faces.active if nothing in history
    if not active_face:
        try:
            af = bm.faces.active
            if af and af.select:
                active_face = af
        except Exception:
            active_face = None

    if not active_face:
        print("Error: No active/reference face found. Make sure you select faces and the reference face last.")
        return False

    selected_faces = [f for f in bm.faces if f.select]
    if len(selected_faces) <= 1:
        print("Error: Select the reference face plus at least one other face.")
        return False

    ref_vert_indices = [v.index for v in active_face.verts]
    me = obj.data
    vgroups = obj.vertex_groups
    if not vgroups:
        print("Error: Object has no Vertex Groups.")
        return False

    # Build weights per group: either average across reference face vertices or from first vertex
    weights = {}
    if use_average:
        for vg in vgroups:
            s = 0.0
            for vi in ref_vert_indices:
                # find weight for this vg on vertex vi
                w = 0.0
                for g in me.vertices[vi].groups:
                    if g.group == vg.index:
                        w = g.weight
                        break
                s += w
            weights[vg.index] = s / len(ref_vert_indices)
    else:
        # take from first vertex of reference face
        vi = ref_vert_indices[0]
        src = {g.group: g.weight for g in me.vertices[vi].groups}
        for vg in vgroups:
            weights[vg.index] = src.get(vg.index, 0.0)

    if only_nonzero_groups:
        weights = {k: v for k, v in weights.items() if v != 0.0}

    if not weights:
        print("Warning: No weights to copy (all zero or no groups).")
        return False

    # Collect target vertices (all vertices of other selected faces)
    target_verts = set()
    for f in selected_faces:
        if f is active_face:
            continue
        for v in f.verts:
            target_verts.add(v.index)

    if not target_verts:
        print("Error: No target vertices found.")
        return False

    # Apply weights in OBJECT mode
    bpy.ops.object.mode_set(mode='OBJECT')
    try:
        for gi, val in weights.items():
            # skip zero weights if filtered
            obj.vertex_groups[gi].add(list(target_verts), val, 'REPLACE')
    finally:
        # return to edit mode and update mesh
        bpy.ops.object.mode_set(mode='EDIT')
        bmesh.update_edit_mesh(obj.data)

    print(f"Done: copied {len(weights)} groups to {len(target_verts)} vertices.")
    return True

# === Run the function ===
# Parameters:
# use_average=True  -> copy average weight across the reference face's vertices (default)
# use_average=False -> copy weights from the first vertex of the reference face
# only_nonzero_groups=False -> if True, don't create groups with zero weight
copy_weights_from_active_face(use_average=True, only_nonzero_groups=False)
