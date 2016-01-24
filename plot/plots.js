function update_plots(mac, name)
{
	divtag = document.getElementById('node_clients');
	ptag = divtag.getElementsByTagName('p')[0];

	plottypes = ['1year', '30d', '24h', '3h'];

	for(i = 0; i < plottypes.length; i++) {
		type = plottypes[i];
		imgtag = ptag.getElementsByClassName(type)[0].children[0];

		imgtag.src = pathprefix + "/clients_" + mac + "_" + type + ".svg";
	}

	h2tag = divtag.getElementsByTagName('h2')[0];
	h2tag.innerHTML = 'Clients an ' + name;
}
