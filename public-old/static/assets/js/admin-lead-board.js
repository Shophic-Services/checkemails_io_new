$(window).on('load', function(){
    var stg_check = 'modalbox'
	if(window.location.hash.indexOf(stg_check) != -1){
        window.location.hash = '#close'
    }
})
$(document).ready(function() {
   
})

function getQueryParams(){
    var vars = {}, hash;
    var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < hashes.length; i++)
    {
        hash = hashes[i].split('=');
        vars[hash[1]] = hash[0] ;
    }
    return vars;
}