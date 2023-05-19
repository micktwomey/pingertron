{ pkgs, ... }:

{
  packages = [ pkgs.git ];

  enterShell = ''
    git --version
    type -a python
    python --version
  '';

  languages.python = {
    enable = true;
    package = pkgs.python311;
    poetry.enable = true;
    poetry.package = pkgs.poetry;
    venv.enable = true;
  };
}
