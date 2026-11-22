"""Command-Line Interface (CLI) for AvatarScript."""
import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import List, Optional
from avatarscript.parser import AvatarSyntaxError
from avatarscript.compiler.validator import AvatarValidationException
from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.renderer.video_exporter import VideoExporter


def _format_source_snippet(source_lines: List[str], line: int, column: int) -> str:
    """Format a 1-indexed line and column with source snippet and caret indicator."""
    if 1 <= line <= len(source_lines):
        src_line = source_lines[line - 1].rstrip("\r\n")
        caret_pos = max(0, column - 1)
        caret_line = " " * caret_pos + "^"
        return f"    {line:4d} | {src_line}\n         | {caret_line}"
    return ""


def _compile_with_diagnostics(script_path: Path, assets_root: Optional[Path] = None):
    if not script_path.exists():
        print(f"Error: Script file not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    source_text = script_path.read_text(encoding="utf-8")
    source_lines = source_text.splitlines()
    compiler = AvatarCompiler(assets_root=assets_root)
    try:
        scene = compiler.compile_source(source_text)
        return scene
    except AvatarSyntaxError as exc:
        snippet = _format_source_snippet(source_lines, exc.loc.line, exc.loc.column)
        print(
            f"[Syntax Error] in {script_path} (Line {exc.loc.line}, Col {exc.loc.column}):\n"
            f"  {exc.message}\n{snippet}",
            file=sys.stderr,
        )
        sys.exit(1)
    except AvatarValidationException as exc:
        print(
            f"[Validation Error] in {script_path} ({len(exc.errors)} error(s)):",
            file=sys.stderr,
        )
        for err in exc.errors:
            snippet = _format_source_snippet(source_lines, err.loc.line, err.loc.column)
            print(f"  - {err}\n{snippet}", file=sys.stderr)
        sys.exit(1)


def cmd_validate(args: argparse.Namespace) -> int:
    script_path = Path(args.script)
    scene = _compile_with_diagnostics(script_path)
    total_frames = int(round(scene.duration * scene.fps))
    print(f"OK: '{script_path}' is valid.")
    print(
        f"  Scene      : {scene.name}\n"
        f"  Resolution : {scene.width}x{scene.height} @ {scene.fps} FPS\n"
        f"  Duration   : {scene.duration}s ({total_frames} frames)\n"
        f"  Avatars    : {', '.join(scene.avatars.keys())}"
    )
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    script_path = Path(args.script)
    scene = _compile_with_diagnostics(script_path)
    from avatarscript.renderer.preview import run_preview

    print(f"Launching Pygame preview for scene '{scene.name}' ({scene.width}x{scene.height} @ {scene.fps} FPS)...")
    run_preview(scene, max_seconds=args.max_seconds)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    script_path = Path(args.script)
    scene = _compile_with_diagnostics(script_path)

    out_path = Path(args.output) if args.output else Path(scene.output_path or f"{scene.name}.mp4")
    total_frames = int(round(scene.duration * scene.fps))
    print(
        f"Rendering scene '{scene.name}' ({scene.width}x{scene.height} @ {scene.fps} FPS, "
        f"{total_frames} frames) -> {out_path} ..."
    )
    exporter = VideoExporter()
    final_path = exporter.export_mp4(scene, output_path=out_path)
    size_kb = final_path.stat().st_size / 1024.0
    print(f"Done! Exported MP4 video to {final_path} ({size_kb:.1f} KB)")
    return 0


def cmd_export_frames(args: argparse.Namespace) -> int:
    script_path = Path(args.script)
    scene = _compile_with_diagnostics(script_path)
    out_dir = Path(args.output)
    transparent = not args.opaque
    mode_label = "transparent RGBA" if transparent else f"opaque ({scene.background})"
    print(
        f"Exporting {mode_label} PNG sequence for scene '{scene.name}' "
        f"({scene.width}x{scene.height} @ {scene.fps} FPS) -> {out_dir}/ ..."
    )
    exporter = VideoExporter()
    files = exporter.export_png_sequence(scene, output_dir=out_dir, transparent=transparent)
    print(f"Done! Exported {len(files)} PNG frames to {out_dir}/")
    return 0


def build_vsix(ext_dir: Path, vsix_path: Path) -> Path:
    """Package vscode-avatarscript into a standard .vsix archive."""
    manifest_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" '
        'xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">\n'
        "  <Metadata>\n"
        '    <Identity Language="en-US" Id="vscode-avatarscript" Version="0.1.0" Publisher="avatarscript"/>\n'
        "    <DisplayName>AvatarScript (.ava) Language Support</DisplayName>\n"
        '    <Description xml:space="preserve">Syntax highlighting, file icons, code snippets, and editor support for AvatarScript (.ava) 2D animated reaction avatar scripts.</Description>\n'
        "    <Tags>avatarscript,ava,animation,avatar,dsl</Tags>\n"
        "    <Categories>Programming Languages,Snippets</Categories>\n"
        "    <GalleryFlags>Public</GalleryFlags>\n"
        "    <Properties>\n"
        '      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.75.0" />\n'
        '      <Property Id="Microsoft.VisualStudio.Services.Icons.Default" Value="extension/icons/avatarscript-logo.png" />\n'
        "    </Properties>\n"
        "    <Icon>extension/icons/avatarscript-logo.png</Icon>\n"
        "  </Metadata>\n"
        "  <Installation>\n"
        '    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>\n'
        "  </Installation>\n"
        "  <Dependencies/>\n"
        "  <Assets>\n"
        '    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />\n'
        '    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true" />\n'
        '    <Asset Type="Microsoft.VisualStudio.Services.Icons.Default" Path="extension/icons/avatarscript-logo.png" Addressable="true" />\n'
        "  </Assets>\n"
        "</PackageManifest>\n"
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="json" ContentType="application/json"/>\n'
        '  <Default Extension="svg" ContentType="image/svg+xml"/>\n'
        '  <Default Extension="png" ContentType="image/png"/>\n'
        '  <Default Extension="md" ContentType="text/markdown"/>\n'
        '  <Default Extension="js" ContentType="application/javascript"/>\n'
        '  <Default Extension="vsixmanifest" ContentType="text/xml"/>\n'
        "</Types>\n"
    )

    with zipfile.ZipFile(vsix_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("extension.vsixmanifest", manifest_xml)
        zf.writestr("[Content_Types].xml", content_types_xml)
        for file_path in sorted(ext_dir.rglob("*")):
            if file_path.is_file() and file_path.suffix != ".vsix":
                rel = file_path.relative_to(ext_dir).as_posix()
                zf.write(file_path, f"extension/{rel}")
    return vsix_path


def cmd_install_extension(args: argparse.Namespace) -> int:
    """Package and install the AvatarScript VS Code / Antigravity extension."""
    ext_dir = Path(__file__).resolve().parent.parent / "vscode-avatarscript"
    if not ext_dir.exists():
        print(f"Error: Extension source directory not found: {ext_dir}", file=sys.stderr)
        return 1

    vsix_path = ext_dir / "vscode-avatarscript-0.1.0.vsix"
    build_vsix(ext_dir, vsix_path)
    print(f"Packaged VSIX archive: {vsix_path} ({vsix_path.stat().st_size / 1024:.1f} KB)")

    home = Path.home()
    target_roots = [
        home / ".vscode" / "extensions",
        home / ".antigravity" / "extensions",
        home / ".cursor" / "extensions",
    ]
    installed_paths = []
    for root in target_roots:
        root.mkdir(parents=True, exist_ok=True)
        dest = root / "avatarscript.vscode-avatarscript-0.1.0"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(ext_dir, dest, ignore=shutil.ignore_patterns("*.vsix"))
        installed_paths.append(dest)
        print(f"Installed extension to: {dest}")

    # Also invoke CLI installers if on PATH
    for cli_bin in ("agy", "code", "cursor"):
        cli_exe = shutil.which(cli_bin)
        if cli_exe:
            try:
                subprocess.run(
                    [cli_exe, "--install-extension", str(vsix_path), "--force"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                    check=False,
                )
            except Exception:
                pass

    print(
        "\nSuccess! AvatarScript (.ava) extension is installed.\n"
        "Press Ctrl+Shift+P -> 'Developer: Reload Window' (or 'Extensions: Install from VSIX...' "
        f"and pick {vsix_path}) to activate syntax colors and icons."
    )
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="avatarscript",
        description="AvatarScript v0.1 — Declarative 2D Animated Reaction Avatar DSL",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate syntax and semantics of an .ava script")
    p_val.add_argument("script", help="Path to .ava script file")
    p_val.set_defaults(func=cmd_validate)

    # preview
    p_prev = subparsers.add_parser("preview", help="Preview an .ava script in a real-time Pygame window")
    p_prev.add_argument("script", help="Path to .ava script file")
    p_prev.add_argument(
        "--max-seconds",
        type=float,
        default=None,
        help="Optional timeout in seconds to automatically close preview",
    )
    p_prev.set_defaults(func=cmd_preview)

    # render
    p_ren = subparsers.add_parser("render", help="Render an .ava script to an H.264 MP4 video")
    p_ren.add_argument("script", help="Path to .ava script file")
    p_ren.add_argument("-o", "--output", help="Override output MP4 path", default=None)
    p_ren.set_defaults(func=cmd_render)

    # export-frames
    p_exp = subparsers.add_parser(
        "export-frames", help="Export an .ava script as a transparent PNG frame sequence"
    )
    p_exp.add_argument("script", help="Path to .ava script file")
    p_exp.add_argument(
        "-o", "--output", required=True, help="Output directory for PNG frames"
    )
    p_exp.add_argument(
        "--opaque",
        action="store_true",
        help="Include scene background color instead of transparent alpha channel",
    )
    p_exp.set_defaults(func=cmd_export_frames)

    # install-extension
    p_ext = subparsers.add_parser(
        "install-extension",
        help="Package and install the AvatarScript (.ava) VS Code / Antigravity extension",
    )
    p_ext.set_defaults(func=cmd_install_extension)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
