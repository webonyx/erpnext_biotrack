## ERPNext BioTrack

BioTrack connector for ERPNext

#### Install
 
* `bench get-app https://github.com/webonyx/erpnext_biotrack`
* `bench --site site_name install-app erpnext_biotrack`

#### Settings

 Desktop > Explore > Setup > Integrations > WA State Compliance Settings
 
> Training Mode for development thought

#### Doctype Mapping

|ERPNext | BioTrack | New |
| --- | --- | --- |
| Item | Inventory | |
| Item Group | Inventory Type | |
| Strain | Strain | Yes |
| Plant | Plant | Yes |
| Customer | Vendor | |
| Warehouse | Room | |
| Delivery Note | Manifest | |


#### License

MIT