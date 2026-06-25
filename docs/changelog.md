## Version 0.7.0 (2026-06-25)

- 🔧 moved from config.yml to config.py setup in package
- 🔧 updated definition of protected bicycle infrastructure to be consistent with other projects (e.g. GrowBikeNet).
- ✨ added declustering step to pipeline
- ✨ set maxgap default value to 1000 for better results

## Version 0.6.0 (2026-05-27)

- 🔧 fix for config.yml in package
- 🔧 solve issues when highway type not in config

## Version 0.5.0 (2026-05-06)

- ✨Initial release ✨
- 🔧Full reimplementation of code from paper "Automated Detection of Missing Links in Bicycle Networks" https://github.com/anastassiavybornova/bikenwgaps
- ⬆️Automated testing via pytest as well as pipeline for package deployment to pip