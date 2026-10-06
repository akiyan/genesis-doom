<a id="en"></a>

EN / [JP](#jp)

# License scope

The combined Doom-derived engine and Genesis ROM are distributed under GNU
GPL version 2; the full text is in `../LICENSE`. Upstream file notices allowing
GPL version 2 or later remain intact and retain that permission. Original
id Software files with legacy Doom Source Code License wording are used under
the GPL v2 grant in the official [DOOM repository](https://github.com/id-Software/DOOM).
This project does not claim to relicense third-party code under MIT.

Independent project-authored files under `tools/`, `boot/`, `toolchain/`,
the Makefiles, and project documentation are MIT licensed under
`MIT.txt`, except copied third-party license texts and screenshots showing
third-party game artwork. Genesis platform files
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

---

<a id="jp"></a>

[EN](#en) / JP

# ライセンスの適用範囲

Doom 派生エンジンと結合した Genesis ROM は GNU GPL version 2 で配布します。
全文は `../LICENSE` にあります。
上流ファイルの GPL version 2 以降を認める表記は保持し、その許諾も維持します。
旧 Doom Source Code License の文言が残る id Software の元ファイルは、公式 [DOOM リポジトリ](https://github.com/id-Software/DOOM) の GPL v2 許諾に基づいて使用しています。
第三者のコードを MIT へ変更するものではありません。

独立した自作の `tools/`、`boot/`、`toolchain/` のファイル、Makefile、プロジェクトの文書には `MIT.txt` を適用します。
コピーした第三者ライセンス本文と、第三者のゲーム画像を含むスクリーンショットは除きます。
`port/engine/` の外にある Genesis プラットフォームファイルは、個別のファイルとして MIT で利用できます。
エンジンと結合した ROM には GPL v2 が適用されます。
既存の第三者の権利表記を優先します。
継承したエンジンファイルへの akiyan の変更と、`port/host/` のホスト検証プログラムは GPL v2 以降で提供します。

SGDK の XGM コードと生成したドライバのバイト列には `SGDK-MIT.txt` を適用します。
Newlib の権利表記は `Newlib.txt` に保持しています。
GCC ランタイムの利用には `GCC-Runtime-Exception.txt` を適用します。
コンパイラとツールチェーンのソースは同梱していません。

ゲームの WAD、画像、音楽は別個の著作物です。
これらのコードライセンスの対象ではなく、現在のソースには含めません。
生成した ROM にはそれらが組み込まれる場合があります。
コードのライセンスだけでは、組み込んだゲーム素材の再配布許可にはなりません。
