# Mark LVI — Plugins

Drop-in plugins live in `plugins/`. Each file defines `PLUGIN` and `run(parameters, player=None, session_memory=None)`.
No core edit is needed to add one — JARVIS discovers plugins at startup.

## Credentials

Plugin credentials are stored under `plugin_config[<namespace>]` in `config/api_keys.json`.
Set them via the settings UI or `memory.config_manager.save_plugin_config`.

## Recently added

- slack_notify, discord_notify — webhook notifications
- obsidian_note, onenote_note, apple_notes, microsoft_todo — notes/tasks
- reddit_post, twitter_post, linkedin_post, instagram_post, twitch_open
- aws_cli, azure_cli, gcp_cli, gitlab_open, bitbucket_open, jenkins_trigger, terraform_run
- figma_open, canva_open, blender_render, davinci_open, audacity_open, handbrake_encode, ffmpeg_convert, plex_open
- quickbooks_open, xero_open, shopify_open, woocommerce_open, wordpress_open, google_analytics_open
- ifttt_trigger, zapier_trigger, hue_control, apple_music_open, netflix_open
