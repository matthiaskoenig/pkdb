
function id_from_url(url){
    var characteristic_id = url.match(/_read\/(\d+)/);
    return characteristic_id[1];
}

function clean(obj) {
    for (var propName in obj) {
        if (obj[propName] === null || obj[propName] === undefined) {
            delete obj[propName];
        }
    }
}
function isEmpty(str) {
    return (!str || 0 === str.length);
}

export {id_from_url, clean,isEmpty};


// vue paginator
const merge_objects = (obj1, obj2) => {
    let obj3 = {};
    for (let attrname in obj1) { obj3[attrname] = obj1[attrname]; }
    for (let attrname in obj2) { obj3[attrname] = obj2[attrname]; }
    return obj3;
};

const getNestedValue = (obj, path) => {
    path = path.split('.');
    let res = obj;
    for (let i = 0; i < path.length; i++) {
        res = res[path[i]]
    }
    //let originalPath = path;
    //if(typeof res === 'undefined') {console.log(`[VuePaginator] Response doesn't contain key ${originalPath}!`)}
    return res
};


export const utils = { merge_objects, getNestedValue };

