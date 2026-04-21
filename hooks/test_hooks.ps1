$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest discover tests/ -v
