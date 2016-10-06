## ERPNext BioTrack

BioTrack connector for ERPNext

#### Install
 
* `bench get-app https://github.com/webonyx/erpnext_biotrack`
* `bench --site site_name install-app erpnext_biotrack`

#### Settings

 Desktop > Explore > Setup > Integrations > WA State Compliance Settings
 
#### Doctype Mapping

|ERPNext | BioTrack | New |
| --- | --- | --- |
| Item | Inventory | |
| Sample | Quality Inspection | |
| Item Group | Inventory Type | |
| Strain | Strain | Yes |
| Plant | Plant | Yes |
| Customer | Vendor | |
| Warehouse | Room | |
| Delivery Note | Manifest | |


#### Enable BioTrack training mode

> bench erpnext_biotrack set-training-mode on|off --site site_name


#### License

MIT