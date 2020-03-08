"""Configure the areas, presets, and channels."""

from .const import (
    CONF_ACTIVE,
    CONF_ACTIVE_INIT,
    CONF_ACTIVE_OFF,
    CONF_ACTIVE_ON,
    CONF_AREA,
    CONF_AREA_OVERRIDE,
    CONF_AUTO_DISCOVER,
    CONF_CHANNEL,
    CONF_CHANNEL_COVER,
    CONF_CHANNEL_TYPE,
    CONF_CLOSE_PRESET,
    CONF_DEFAULT,
    CONF_DEVICE_CLASS,
    CONF_DURATION,
    CONF_FADE,
    CONF_HIDDEN_ENTITY,
    CONF_HOST,
    CONF_NAME,
    CONF_NO_DEFAULT,
    CONF_OPEN_PRESET,
    CONF_POLL_TIMER,
    CONF_PORT,
    CONF_PRESET,
    CONF_ROOM,
    CONF_ROOM_OFF,
    CONF_ROOM_ON,
    CONF_STOP_PRESET,
    CONF_TEMPLATE,
    CONF_TILT_TIME,
    CONF_TIME_COVER,
    CONF_TRIGGER,
    DEFAULT_CHANNEL_TYPE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_PRESETS,
    DEFAULT_TEMPLATES,
)

PRESET_CONFS = {
    CONF_ROOM: [CONF_ROOM_ON, CONF_ROOM_OFF],
    CONF_TRIGGER: [CONF_TRIGGER],
    CONF_TIME_COVER: [CONF_OPEN_PRESET, CONF_CLOSE_PRESET, CONF_STOP_PRESET],
}

TIME_COVER_VALUE_CONFS = [CONF_DEVICE_CLASS, CONF_DURATION, CONF_TILT_TIME]


class DynaliteConfig:
    """Configure the Dynalite bridge."""

    def __init__(self, config):
        """Configure the Dynalite bridge."""
        # insert the global values
        self.host = config.get(CONF_HOST, "localhost")  # Default value for testing
        self.port = config.get(CONF_PORT, DEFAULT_PORT)
        self.name = config.get(CONF_NAME, f"{DEFAULT_NAME}-{self.host}")
        self.auto_discover = config.get(CONF_AUTO_DISCOVER, False)
        self.active = config.get(CONF_ACTIVE, CONF_ACTIVE_INIT)
        if self.active is True:
            self.active = CONF_ACTIVE_ON
        if self.active is False:
            self.active = CONF_ACTIVE_OFF
        self.poll_timer = config.get(CONF_POLL_TIMER, 1.0)
        self.default_fade = config.get(CONF_DEFAULT, {}).get(CONF_FADE, 0)
        # create the templates
        config_templates = config.get(CONF_TEMPLATE, {})
        templates = {}
        for template in DEFAULT_TEMPLATES:
            templates[template] = {}
            cur_template = config_templates.get(template, {})
            for conf in DEFAULT_TEMPLATES[template]:
                templates[template][conf] = cur_template.get(
                    conf, DEFAULT_TEMPLATES[template][conf]
                )
        # create default presets
        config_presets = config.get(CONF_PRESET, DEFAULT_PRESETS)
        default_presets = {
            int(preset): self.configure_preset(
                preset, config_presets[preset], self.default_fade
            )
            for preset in config_presets
        }
        # create the areas with their channels and presets
        self.area = {}
        for area_val in config.get(CONF_AREA, {}):  # may be a string '123'
            area = int(area_val)
            area_config = config[CONF_AREA].get(area_val)
            self.area[area] = self.configure_area(
                area, area_config, self.default_fade, templates, default_presets
            )

    @staticmethod
    def configure_preset(preset, preset_config, default_fade, hidden=False):
        """Return the configuration of a preset."""
        result = {
            CONF_NAME: preset_config.get(CONF_NAME, f"Preset {preset}"),
            CONF_FADE: preset_config.get(CONF_FADE, default_fade),
        }
        if hidden:
            result[CONF_HIDDEN_ENTITY] = True
        return result

    @staticmethod
    def configure_channel(channel, channel_config, default_fade, hidden=False):
        """Return the configuration of a channel."""
        result = {
            CONF_NAME: channel_config.get(CONF_NAME, f"Channel {channel}"),
            CONF_FADE: channel_config.get(CONF_FADE, default_fade),
            CONF_CHANNEL_TYPE: channel_config.get(
                CONF_CHANNEL_TYPE, DEFAULT_CHANNEL_TYPE
            ),
        }
        if hidden:
            result[CONF_HIDDEN_ENTITY] = True
        return result

    @staticmethod
    def configure_area(area, area_config, default_fade, templates, default_presets):
        """Return the configuration of an area."""
        result = {
            CONF_NAME: area_config.get(CONF_NAME, f"Area {area}"),
            CONF_FADE: area_config.get(CONF_FADE, default_fade),
        }
        for conf in [CONF_TEMPLATE, CONF_AREA_OVERRIDE]:
            if conf in area_config:
                result[conf] = area_config[conf]
        # User defined presets and channels first, then template presets, then defaults
        area_presets = {
            int(preset): DynaliteConfig.configure_preset(
                preset, area_config[CONF_PRESET][preset], result[CONF_FADE]
            )
            for preset in area_config.get(CONF_PRESET, {})
        }
        area_channels = {
            int(channel): DynaliteConfig.configure_channel(
                channel, area_config[CONF_CHANNEL][channel], result[CONF_FADE]
            )
            for channel in area_config.get(CONF_CHANNEL, {})
        }
        # add the entities implicitly defined by templates
        template = area_config.get(CONF_TEMPLATE)
        if template:
            # ensure presets are there
            for conf in PRESET_CONFS[template]:
                preset = int(area_config.get(conf, templates[template][conf]))
                result[conf] = preset
                if preset not in area_presets:
                    area_presets[preset] = DynaliteConfig.configure_preset(
                        preset, {}, result[CONF_FADE], template != CONF_TRIGGER
                    )
        if template == CONF_TIME_COVER:  # time cover also has non-preset conf
            for conf in TIME_COVER_VALUE_CONFS:
                result[conf] = area_config.get(conf, templates[template][conf])
            channel_cover = int(
                area_config.get(
                    CONF_CHANNEL_COVER, templates[template][CONF_CHANNEL_COVER]
                )
            )
            result[CONF_CHANNEL_COVER] = channel_cover
            if 0 < channel_cover < 255 and channel_cover not in area_channels:
                area_channels[channel_cover] = DynaliteConfig.configure_channel(
                    channel_cover, {}, result[CONF_FADE], True
                )
        # Default presets
        if not area_config.get(CONF_NO_DEFAULT, False) and not template:
            for preset in default_presets:
                if preset not in area_presets:
                    area_presets[preset] = default_presets[preset]
        result[CONF_PRESET] = area_presets
        result[CONF_CHANNEL] = area_channels
        return result
