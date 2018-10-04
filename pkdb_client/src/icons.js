
const icons_table = {
    home: 'home',
    studies: 'procedures',
    study: 'procedure',
    groups: 'users',
    group: 'user',
    individuals: 'user',
    individual: 'user',
    interventions: 'capsules',
    intervention: 'capsule',
    outputs: 'chart-bar',
    output: 'chart-bar',
    timecourses: 'chart-line',
    timecourse: 'chart-line',
    references: 'file-alt',
    reference: 'file-alt',
    about: 'info-circle',
    api: 'code',
    admin: 'cogs',
    account: 'user-circle',
};

function lookup_icon(key){
    return icons_table[key]
}

/**
 * Lookup icon from given font-awesome branch which can be used in md-icon context.
 * font-awesome: 5.3.1
 */
function lookup_md_icon(key){

    if (key === 'home'){
        return require('./assets/images/fontawesome/svgs/solid/home.svg')
    }
    else if (['studies', 'study'].indexOf(key) >= 0){
        return require('./assets/images/fontawesome/svgs/solid/procedures.svg')
    }
    else if (['groups', 'group'].indexOf(key) >= 0){
        return require('./assets/images/fontawesome/svgs/solid/users.svg')
    }
    else if (['individuals', 'individual'].indexOf(key) >= 0){
        return require('./assets/images/fontawesome/svgs/solid/user.svg')
    }
    else if (key === 'interventions'){
        return require('./assets/images/fontawesome/svgs/solid/capsules.svg')
    }
    else if (key === 'intervention'){
        return require('./assets/images/fontawesome/svgs/solid/capsules.svg')
    }
    else if (['outputs', 'output'].indexOf(key) >= 0){
        return require('./assets/images/fontawesome/svgs/solid/chart-bar.svg')
    }
    else if (['timecourses', 'timecourse'].indexOf(key) >= 0){
        return require('./assets/images/fontawesome/svgs/solid/chart-line.svg')
    }
    else if (['references', 'reference'].indexOf(key) >= 0){
        return require('./assets/images/fontawesome/svgs/solid/file-alt.svg')
    }
    else if (key === 'about'){
        return require('./assets/images/fontawesome/svgs/solid/info-circle.svg')
    }
    else if (key === 'api') {
        return require('./assets/images/fontawesome/svgs/solid/code.svg')
    }
    else if (key === 'github'){
        return require('./assets/images/fontawesome/svgs/brands/github.svg')
    }
    else if (key === 'admin'){
        return require('./assets/images/fontawesome/svgs/solid/cogs.svg')
    }
    else if (key === 'account'){
        return require('./assets/images/fontawesome/svgs/solid/user-circle.svg')
    }
    // default value
    else {
        return require('./assets/images/fontawesome/svgs/solid/circle.svg')
    }
}

export {lookup_icon, lookup_md_icon};