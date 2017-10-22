SELECT count(*) FROM mangos.item_template where 
(bonding=1 or bonding=2 or bonding=3);

Update mangos.item_template set bonding=0 where (bonding=1 or bonding=2 or bonding=3);