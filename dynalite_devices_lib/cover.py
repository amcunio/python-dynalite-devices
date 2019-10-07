"""Support for the Dynalite channels as covers."""
import asyncio
import logging
from .const import DOMAIN, LOGGER, CONF_COVERS

from .dynalitebase import DynaliteChannelBaseDevice

class DynaliteChannelCoverDevice(DynaliteChannelBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant Cover."""

    def __init__(self, area, channel, name, type, device_class, cover_factor, master_area, bridge, device):
        """Initialize the cover."""
        self._device_class = device_class
        self._cover_factor = cover_factor
        self._actual_level = 0
        self._target_level = 0
        self._current_position = 0
        super().__init__(area, channel, name, type, master_area, bridge, device)

    @property
    def category(self):
        return 'cover'
        
    @property
    def device_class(self):
        return self._device_class

    def update_level(self, actual_level, target_level):
        prev_actual_level = self._actual_level
        self._actual_level = actual_level
        self._target_level = target_level
        level_diff = actual_level - prev_actual_level
        factored_diff = level_diff / self._cover_factor
        self._current_position = min(1, max(0, self._current_position + factored_diff))
        if self._current_position > 0.99999:
            self._current_position = 1
        if self._current_position < 0.00001:
            self._current_position = 0
        if getattr(self, 'update_tilt', False):
            self.update_tilt(factored_diff)
        
    @property
    def current_cover_position(self):
        """return the position of the cover from 0 to 100"""
        return int(self._current_position * 100)

    @property
    def is_opening(self):
        return self._target_level > self._actual_level
        
    @property
    def is_closing(self):
        return self._target_level < self._actual_level
        
    @property
    def is_closed(self):
        return self._current_position == 0

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self._device.turnOn()
        
    async def async_close_cover(self, **kwargs):
        """Open the cover."""
        self._device.turnOff()

    async def async_set_cover_position(self, **kwargs):
        """Open the cover."""
        # LOGGER.debug("XXX async_set_cover_position params=%s", pprint.pformat(kwargs))
        target_position = kwargs[ATTR_POSITION] / 100
        position_diff = target_position - self._current_position
        level_diff = position_diff * self._cover_factor
        target_level = min(1, max(0, self._actual_level + level_diff))
        self._device.turnOn(brightness = target_level)
        
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self._device.stopFade()

class DynaliteChannelCoverWithTiltDevice(DynaliteChannelCoverDevice):
    """Representation of a Dynalite Channel as a Home Assistant Cover that uses up and down for tilt."""

    def __init__(self, area, channel, name, type, device_class, cover_factor, tilt_percentage, master_area, bridge, device):
        super().__init__(area, channel, name, type, device_class, cover_factor, master_area, bridge, device)
        self._tilt_percentage = tilt_percentage
        self._current_tilt = 0
        
    def update_tilt(self, diff):
        tilt_diff = diff / self._tilt_percentage
        self._current_tilt = max(0, min(1, self._current_tilt + tilt_diff))

    @property
    def current_cover_tilt_position(self):
        return int(self._current_tilt * 100)
    
    async def apply_tilt_diff(self, tilt_diff):
        position_diff = tilt_diff * self._tilt_percentage
        target_position = int(100 * max(0, min(1, self._current_position + position_diff)))
        await self.async_set_cover_position(position=target_position)
    
    async def async_open_cover_tilt(self, **kwargs):
        if self._current_tilt == 1:
            return
        else:
            await self.apply_tilt_diff(1 - self._current_tilt)

    async def async_close_cover_tilt(self, **kwargs):
        if self._current_tilt == 0:
            return
        else:
            await self.apply_tilt_diff(0 - self._current_tilt)

    async def async_set_cover_tilt_position(self, **kwargs):
        target_position = kwargs[ATTR_TILT_POSITION] / 100
        await self.apply_tilt_diff(target_position - self._current_tilt)
        
    async def async_stop_cover_tilt(self, **kwargs):
        await self.async_stop_cover()
