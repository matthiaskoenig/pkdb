
function id_from_url(url){
    var characteristic_id = url.match(/characteristica_read\/(\d+)/);
    return characteristic_id[1];
}

function clean(obj) {
    for (var propName in obj) {
        if (obj[propName] === null || obj[propName] === undefined) {
            delete obj[propName];
        }
    }
}
export {id_from_url, clean}