# Alfalab

https://alfalab-dev.solsdev.com/
https://alfalab.solsdev.com/



## Addons development

Add odoo addon under `addons` folder as a:
  
  - subfolder; or
  - as git submodule

Push changes to addons to trigger the deployment on sandbox server.
For manual deployment, use Github action: https://github.com/Odoo-Alfalab/odoo-alfalab/actions/workflows/ci_dev.yml and use `Run workflow` button. Select `develop` for branch option.

SANDBOX:
http://ec2-3-79-91-190.eu-central-1.compute.amazonaws.com:8269

PROD:
https://era.solsplatform.eu/
