# License scope

The combined Doom-derived engine and Genesis ROM are distributed under GNU
GPL version 2; the full text is in `../LICENSE`. Upstream file notices allowing
GPL version 2 or later remain intact and retain that permission. Original
id Software files with legacy Doom Source Code License wording are used under
the GPL v2 grant in the official [DOOM repository](https://github.com/id-Software/DOOM).
This project does not claim to relicense third-party code under MIT.

Independent project-authored files under `tools/`, `boot/`, `toolchain/`,
the Makefiles, and project documentation are MIT licensed under
`MIT.txt`, except copied third-party license texts. Genesis platform files
outside `port/engine/` are available under MIT as individual files; a combined
engine/ROM remains subject to GPL v2. Existing third-party notices take precedence.
Changes by akiyan to inherited engine files and the host engine harness under
`port/host/` are offered under GPL v2 or later.

SGDK XGM code and generated driver bytes are covered by `SGDK-MIT.txt`.
Newlib notices are retained in `Newlib.txt`. GCC runtime use is covered by
`GCC-Runtime-Exception.txt`; compiler/toolchain sources are not vendored here.
Game WADs, images and music are separate copyrighted inputs. They are not
covered by these code licenses and are not included in the current source snapshot.
Generated ROMs may contain those inputs; code licensing does not establish
permission to redistribute the incorporated game assets.
