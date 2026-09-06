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
    
    def __init__(self, length, width, height, profile_size):
        """Initialize calculator with frame dimensions.
        
        Parameters
        ----------
        length : float
            Frame outer dimension along X (mm)
        width : float
            Frame outer dimension along Y (mm)
        height : float
            Frame outer dimension along Z (mm)
        profile_size : float
            Profile width/height (mm)
        """
        self.length = length
        self.width = width
        self.height = height
        self.profile_size = profile_size
        
        # Calculate Z post anchor (first post position)
        self._calc_z_post_anchor()
        
    def _calc_z_post_anchor(self):
        """Calculate Z post anchor position (first post)."""
        # Z post first position formula:
        # X = -profile_size/2 - (length - profile_size)/2
        # Y = -profile_size/2 - (width - profile_size)/2
        self.z_post_anchor_x = -self.profile_size/2 - (self.length - self.profile_size)/2
        self.z_post_anchor_y = -self.profile_size/2 - (self.width - self.profile_size)/2
        self.z_post_anchor_z = 0
        
    # ========== Z Posts ==========
    def get_z_post_positions(self):
        """Get all 4 Z post positions.
        
        Returns
        -------
        list of tuples
            [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
        """
        spacing_x = self.length - self.profile_size
        spacing_y = self.width - self.profile_size
        
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
        return (self.length - self.profile_size, self.width - self.profile_size)
    
    # ========== X Beams ==========
    def get_x_beam_placement(self):
        """Get X beam array placement.
        
        Y position is flush with the Z post band (aligned to post outer face).
        """
        # Y = Z_post_anchor_y + profile_size/2
        y_start = self.z_post_anchor_y + self.profile_size / 2
        return (0, y_start, 0)
    
    def get_x_beam_spacing(self):
        """Get X beam array spacing in Y direction."""
        return self.width - self.profile_size
    
    def get_x_beam_length(self):
        """Get X beam length."""
        return self.length - 2 * self.profile_size
    
    # ========== Y Beams ==========
    def get_y_beam_placement(self):
        """Get Y beam array placement.
        
        X position is flush with the Z post band (aligned to post outer face).
        """
        # X = Z_post_anchor_x + profile_size/2
        x_start = self.z_post_anchor_x + self.profile_size / 2
        return (x_start, 0, 0)
    
    def get_y_beam_spacing(self):
        """Get Y beam array spacing in X direction."""
        return self.length - self.profile_size
    
    def get_y_beam_length(self):
        """Get Y beam length."""
        return self.width - 2 * self.profile_size
    
    # ========== Z Layers ==========
    def get_z_layer_spacing(self, z_layers):
        """Get Z layer spacing."""
        if z_layers <= 0:
            z_layers = 1
        return (self.height - self.profile_size) / z_layers
    
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
