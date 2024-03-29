# -*- coding: utf-8 -*-
from typing import Mapping, Any, Sequence

from bag.layout.template import TemplateDB
from bag.layout.util import BBox
from bag.util.immutable import Param
from bag.typing import PointType

from pybag.enum import PathStyle

from ..inductor.util import compute_vertices, IndTemplate


class TcoilDiffRing(IndTemplate):
    """Differential t-coil Ring, 'R0' orientation"""
    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        IndTemplate.__init__(self, temp_db, params, **kwargs)
        self._turn_coords = []

    @property
    def turn_coords(self) -> Sequence[PointType]:
        return self._turn_coords

    @classmethod
    def get_params_info(cls) -> Mapping[str, str]:
        return dict(
            lay_id='Tcoil top layer ID',
            bot_lay_id='Tcoil bot layer ID; same as top layer by default',
            width='Metal width for ring',
            gap='Gap in ring at bottom for inductor leads',
            gap_t='Gap in ring at top for inductor leads',
            radius_x='radius along X-axis',
            radius_y='radius along Y-axis',
            ring_sup='supply name for ring; VSS by default',
        )

    @classmethod
    def get_default_param_values(cls) -> Mapping[str, Any]:
        return dict(
            bot_lay_id=-1,
            ring_sup='VSS',
        )

    def draw_layout(self) -> None:
        lay_id: int = self.params['lay_id']
        lp = self.grid.tech_info.get_lay_purp_list(lay_id)[0]

        bot_lay_id: int = self.params['bot_lay_id']
        if bot_lay_id < 1:
            bot_lay_id = lay_id

        width: int = self.params['width']
        gap: int = self.params['gap']
        gap_t: int = self.params['gap_t']
        radius_x: int = self.params['radius_x']
        radius_y: int = self.params['radius_y']
        ring_sup: str = self.params['ring_sup']

        vertices = compute_vertices(4, 1, radius_x, radius_y, width, 0)[0]

        # Compute path co-ordinates
        off_x = radius_x + width // 2
        gap2 = -(- gap // 2)
        gap2_t = -(- gap_t // 2)
        _turn_r = [(off_x + gap2, vertices[0][1]), vertices[0], vertices[1], (off_x + gap2_t, vertices[1][1])]
        _turn_l = [(off_x - gap2_t, vertices[-2][1]), vertices[-2], vertices[-1], (off_x - gap2, vertices[-1][1])]
        self.add_path(lp, width, _turn_r, PathStyle.extend, join_style=PathStyle.extend)
        self.add_path(lp, width, _turn_l, PathStyle.extend, join_style=PathStyle.extend)

        # --- complete guard ring on (lay_id - 1) --- #
        #     R0
        #   2-----1
        #   |     |
        #   |     |
        #   3-----0
        self._draw_bridge(_turn_l[-1], _turn_r[0], lay_id, lay_id, lay_id - 1, width, PathStyle.extend)
        self._draw_bridge(_turn_l[0], _turn_r[-1], lay_id, lay_id, lay_id - 1, width, PathStyle.extend)

        ring_path = [vertices[0]]
        ring_path[0:0] = vertices
        off_y = radius_y + width // 2
        _bbox_l = BBox(vertices[2][0] - width // 2, off_y - width, vertices[2][0] + width // 2, off_y + width)
        _bbox_r = BBox(vertices[0][0] - width // 2, off_y - width, vertices[0][0] + width // 2, off_y + width)
        for _lay_id in range(lay_id - 1, bot_lay_id - 1, -1):
            # draw rings on all layers below lay_id
            _lp = self.grid.tech_info.get_lay_purp_list(_lay_id)[0]
            self.add_path(_lp, width, ring_path, PathStyle.extend, join_style=PathStyle.extend)

            # via to upper layer ring
            top_lp = self.grid.tech_info.get_lay_purp_list(_lay_id + 1)[0]
            _dir = self.grid.get_direction(_lay_id)
            self.add_via(_bbox_l, _lp, top_lp, _dir, extend=False)
            self.add_via(_bbox_r, _lp, top_lp, _dir, extend=False)

        # add ring pin below leads for return path in EM sim
        bot_lp = self.grid.tech_info.get_lay_purp_list(lay_id - 1)[0]
        pin_bbox = BBox(off_x - gap2, _turn_r[0][1] - width // 2, off_x + gap2, _turn_r[0][1] + width // 2)
        pin_bbox1 = BBox(off_x - gap2_t, _turn_l[0][1] - width // 2, off_x + gap2_t, _turn_l[0][1] + width // 2)
        self.add_pin_primitive(ring_sup, bot_lp[0], pin_bbox)
        self.add_pin_primitive(ring_sup, bot_lp[0], pin_bbox1)

        # set attributes for _draw_fill() using ring co-ordinates
        # hack: setup ring co-ordinates like inductor to re-use _draw_fill method
        _turn = [(off_x + gap2, vertices[0][1]), (off_x - gap2, vertices[-1][1])]
        _turn[1:1] = vertices
        self._turn_coords = _turn

        # set size
        self._actual_bbox = BBox(0, 0, 2 * radius_x + width, 2 * radius_y + width)
        self.set_size_from_bound_box(lay_id, self._actual_bbox, round_up=True)
