{ pkgs, ... }:

{
  packages = [
    pkgs.git
    pkgs.prometheus
  ];

  scripts.pingertron-prometheus.exec = ''
    mkdir -p /tmp/pingertron-prometheus
    ${pkgs.prometheus}/bin/prometheus \
      --config.file $DEVENV_ROOT/examples/prometheus.yml \
      --web.listen-address=127.0.0.1:9090 \
      --storage.tsdb.path /tmp/pingertron-prometheus
  '';

  processes = {
    prometheus.exec = "pingertron-prometheus";
  };

  enterShell = ''
    git --version
    # type -a python
    python --version
    poetry install
  '';

  languages.python = {
    enable = true;
    package = pkgs.python311;
    poetry.enable = true;
    poetry.package = pkgs.poetry;
    venv.enable = true;
  };
}
