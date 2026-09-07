{
  lib,
  stdenvNoCC,
  fetchurl,
  unzip,
  installShellFiles,
  variant ? "tunnel-client",
  installShellCompletions ? stdenvNoCC.buildPlatform.canExecute stdenvNoCC.hostPlatform,
}:
let
  release = builtins.fromJSON (builtins.readFile ./release.json);
  platforms = builtins.fromJSON (builtins.readFile ./platforms.json);
  variants = builtins.fromJSON (builtins.readFile ./variants.json);
  settings = variants.${variant};
  platform = platforms.${stdenvNoCC.hostPlatform.system}.asset;
  archive = "${variant}-v${release.version}-${platform}";
in
stdenvNoCC.mkDerivation {
  pname = variant;
  inherit (release) version;

  src = fetchurl {
    url = "https://github.com/openai/tunnel-client/releases/download/v${release.version}/${archive}.zip";
    hash = release.hashes.${variant}.${platform};
  };

  sourceRoot = "source";
  unpackPhase = ''
    runHook preUnpack
    mkdir source
    unzip -q "$src" -d source
    runHook postUnpack
  '';
  nativeBuildInputs = [ unzip ] ++ lib.optional installShellCompletions installShellFiles;
  dontBuild = true;
  dontConfigure = true;
  # Preserve upstream signatures and embedded binary metadata.
  dontStrip = true;
  dontPatchELF = true;

  installPhase = ''
    runHook preInstall
    install -Dm755 ${variant} "$out/libexec/${variant}/${variant}"
    mkdir -p "$out/bin"
    ln -s ../libexec/${variant}/${variant} "$out/bin/${variant}"
    ${lib.optionalString settings.cloudflared ''
      # Upstream locates its companion relative to the real executable.
      install -m755 cloudflared "$out/libexec/${variant}/cloudflared"
      install -m644 cloudflared-manifest.json "$out/libexec/${variant}/cloudflared-manifest.json"
    ''}
    install -Dm644 LICENSE "$out/share/doc/${variant}/LICENSE"
    install -m644 NOTICE ${archive}-licenses.txt ${archive}.spdx.json "$out/share/doc/${variant}/"
    ${lib.optionalString (installShellCompletions && settings.completions) ''
      for shell in bash fish zsh; do
        "$out/bin/${variant}" completion "$shell" > "completion.$shell"
      done
      installShellCompletion --cmd ${variant} \
        --bash completion.bash --fish completion.fish --zsh completion.zsh
    ''}
    runHook postInstall
  '';

  doInstallCheck = stdenvNoCC.buildPlatform.canExecute stdenvNoCC.hostPlatform;
  installCheckPhase = ''
    runHook preInstallCheck
    "$out/bin/${variant}" --version | grep -F '${release.version}'
    "$out/bin/${variant}" --help > /dev/null
    ${lib.optionalString settings.cloudflared ''
      "$out/libexec/${variant}/cloudflared" --version
    ''}
    runHook postInstallCheck
  '';

  meta = {
    description = "OpenAI Secure MCP Tunnel client (${variant})";
    homepage = "https://github.com/openai/tunnel-client";
    changelog = "https://github.com/openai/tunnel-client/releases/tag/v${release.version}";
    license = lib.licenses.asl20;
    platforms = builtins.attrNames platforms;
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
    mainProgram = variant;
  };
}
