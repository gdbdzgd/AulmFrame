# -*- coding: utf-8 -*-
"""
Position calculation module for Aluminum Frame Generator.
Centralizes all position calculations based on frame properties and Z post anchor.
"""

try:
    from FreeCAD import Base
except ImportError:
    Base = None


class FramePositionCalculator:
    """Calculator for all frame component positions.
    
    All positions are calculated relative to the Z post anchor point (first Z post).
    This ensures perfect alignment between beams and posts.
    """
    
    def __init__(self, length, width, height, profile_size, profile_height=None,
                 post_along_x='a', beam_vertical='b'):
        """Initialize calculator with frame dimensions and section orientation.

        Parameters
        ----------
        length : float
            Frame outer dimension along X (mm)
        width : float
            Frame outer dimension along Y (mm)
        height : float
            Frame outer dimension along Z (mm)
        profile_size : float
            Cross-section dimension ``a`` (first, mm)
        profile_height : float, optional
            Cross-section dimension ``b`` (second, mm). Defaults to ``a``.
        post_along_x : {'a', 'b'}
            Which section dimension the Z post uses along frame X. The other
            dimension is then used along Y. Ignored for square sections.
        beam_vertical : {'a', 'b'}
            Which section dimension the X/Y beams use vertically. The other
            dimension becomes the horizontal transverse size.
        """
        self.length = length
        self.width = width
        self.height = height
        self.a = profile_size
        self.b = profile_size if profile_height is None else profile_height
        self.profile_size = self.a
        self.profile_height = self.b
        self.post_along_x = post_along_x if post_along_x in ('a', 'b') else 'a'
        self.beam_vertical = beam_vertical if beam_vertical in ('a', 'b') else 'b'

        # Post extents per frame axis
        if self.post_along_x == 'a':
            self.px, self.py = self.a, self.b
        else:
            self.px, self.py = self.b, self.a

        # Horizontal beam cross-section: vertical + transverse
        if self.beam_vertical == 'a':
            self.v, self.t = self.a, self.b
        else:
            self.v, self.t = self.b, self.a

        # Backward-compatible aliases
        self.pw = self.px
        self.ph = self.py

        # Calculate Z post anchor (first post position)
        self._calc_z_post_anchor()

    def _calc_z_post_anchor(self):
        """Calculate Z post anchor position (first post)."""
        self.z_post_anchor_x = -self.px / 2 - (self.length - self.px) / 2
        self.z_post_anchor_y = -self.py / 2 - (self.width - self.py) / 2
        self.z_post_anchor_z = 0

    def get_post_section(self):
        """Return the post cross-section (extent along X, extent along Y)."""
        return (self.px, self.py)

    def get_beam_section(self):
        """Return the horizontal beam cross-section (transverse, vertical)."""
        return (self.t, self.v)

    # ========== Z Posts ==========
    def get_z_post_positions(self):
        """Get all 4 Z post positions.

        Returns
        -------
        list of tuples
            [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
        """
        spacing_x = self.length - self.px
        spacing_y = self.width - self.py

        positions = [
            (self.z_post_anchor_x, self.z_post_anchor_y),  # First post
            (self.z_post_anchor_x + spacing_x, self.z_post_anchor_y),  # Second post
            (self.z_post_anchor_x, self.z_post_anchor_y + spacing_y),  # Third post
            (self.z_post_anchor_x + spacing_x, self.z_post_anchor_y + spacing_y),  # Fourth post
        ]
        return positions

    def get_z_post_placement(self):
        """Get Z post array placement."""
        return (self.z_post_anchor_x, self.z_post_anchor_y, self.z_post_anchor_z)

    def get_z_post_spacing(self):
        """Get Z post array spacing."""
        return (self.length - self.px, self.width - self.py)

    # ========== X Beams ==========
    def get_x_beam_placement(self):
        """Get X beam array placement.

        Y position is the Z post centre line (post extent along Y = py).
        """
        y_start = self.z_post_anchor_y + self.py / 2
        return (0, y_start, 0)

    def get_x_beam_spacing(self):
        """Get X beam array spacing in Y direction."""
        return self.width - self.py

    def get_x_beam_length(self):
        """Get X beam length (between post inner faces along X)."""
        return self.length - 2 * self.px

    # ========== Y Beams ==========
    def get_y_beam_placement(self):
        """Get Y beam array placement.

        X position is the Z post centre line (post extent along X = px).
        """
        x_start = self.z_post_anchor_x + self.px / 2
        return (x_start, 0, 0)

    def get_y_beam_spacing(self):
        """Get Y beam array spacing in X direction."""
        return self.length - self.px

    def get_y_beam_length(self):
        """Get Y beam length (between post inner faces along Y)."""
        return self.width - 2 * self.py

    # ========== Z Layers ==========
    def get_z_layer_spacing(self, z_layers):
        """Get Z layer spacing (beam vertical extent = v)."""
        if z_layers <= 0:
            z_layers = 1
        return (self.height - self.v) / z_layers
    
    def get_z_layer_positions(self, z_layers):
        """Get Z positions for all layers."""
        if z_layers <= 0:
            z_layers = 1
        spacing = self.get_z_layer_spacing(z_layers)
        return [i * spacing for i in range(z_layers + 1)]
    
    # ========== Summary ==========
    def get_summary(self, z_layers=1):
        """Get complete position summary."""
        return {
            'z_post_anchor': (self.z_post_anchor_x, self.z_post_anchor_y, self.z_post_anchor_z),
            'z_post_positions': self.get_z_post_positions(),
            'z_post_spacing': self.get_z_post_spacing(),
            'x_beam_placement': self.get_x_beam_placement(),
            'x_beam_spacing': self.get_x_beam_spacing(),
            'x_beam_length': self.get_x_beam_length(),
            'y_beam_placement': self.get_y_beam_placement(),
            'y_beam_spacing': self.get_y_beam_spacing(),
            'y_beam_length': self.get_y_beam_length(),
            'z_layer_positions': self.get_z_layer_positions(z_layers),
            'z_layer_spacing': self.get_z_layer_spacing(z_layers),
        }
