import axios from 'axios'

function id_from_url(url) {
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

function fetch_data(url) {
    axios.get(url)
        .then(response => {
            return response.data
        })
        .catch((error) => {
            console.error(error);
        })
}

export {id_from_url, clean, isEmpty, fetch_data};


// vue paginator
const merge_objects = (obj1, obj2) => {
    let obj3 = {};
    for (let attrname in obj1) {
        obj3[attrname] = obj1[attrname];
    }
    for (let attrname in obj2) {
        obj3[attrname] = obj2[attrname];
    }
    return obj3;
};

const getNestedValue = (obj, path) => {
    path = path.split('.');
    let res = obj;
    for (let i = 0; i < path.length; i++) {
        res = res[path[i]]
    }

    return res
};

function toNumber(num){
    // round to two numbers
    return +(Math.round(num + "e+2")  + "e-2");
}

function timeObject(item) {
    return{
        name: "t = " + toNumber(item.time) + ' ' + item.time_unit,
        otype: "time",
    }
}


export const utils = {merge_objects, getNestedValue, timeObject};

