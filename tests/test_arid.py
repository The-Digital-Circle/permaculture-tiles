import numpy as np
from scripts.build_arid import arid_class_mask

def test_koppen_b_classes_are_arid():
    # Beck et al. class ids: 4=BWh 5=BWk 6=BSh 7=BSk are the arid 'B' climates
    grid = np.array([[1, 3, 4], [5, 6, 7], [8, 14, 29]], dtype=np.uint8)
    m = arid_class_mask(grid)
    assert m[0, 2] and m[1, 0] and m[1, 1] and m[1, 2]     # 4,5,6,7 -> arid
    assert not m[0, 0] and not m[0, 1] and not m[2, 0]     # 1,3,8 -> not arid
