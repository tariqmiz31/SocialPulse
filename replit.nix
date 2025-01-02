{pkgs}: {
  deps = [
    pkgs.nginx
    pkgs.pm2
    pkgs.python3
    pkgs.nodejs
    pkgs.lsof
    pkgs.procps
    pkgs.postgresql
  ];
}
