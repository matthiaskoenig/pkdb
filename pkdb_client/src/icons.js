/*
const icons_table = {

};

function lookup_icon(key){
    return null
}
*/

/**
 * Lookup icon from given font-awesome branch which can be used in md-icon context.
 */
function lookup_md_icon(key){

    /*
    if (key == 'home'){
        return require('./assets/images/fontawesome/svgs/solid/home.svg')
    }
    */
    /*
    user () {
        return require('../assets/images/fontawesome/svgs/solid/user.svg')
    },
    user_circle () {
        return require('../assets/images/fontawesome/svgs/solid/user-circle.svg')
    },
    users () {
        return require('../assets/images/fontawesome/svgs/solid/users.svg')
    },
    capsules () {
        return require('../assets/images/fontawesome/svgs/solid/capsules.svg')
    },
    code () {
        return require('../assets/images/fontawesome/svgs/solid/code.svg')
    },
    cogs () {
        return require('../assets/images/fontawesome/svgs/solid/cogs.svg')
    },
    procedures () {
        return require('../assets/images/fontawesome/svgs/solid/procedures.svg')
    },
    chart_bar () {
        return require('../assets/images/fontawesome/svgs/solid/chart-bar.svg')
    },
    chart_line () {
        return require('../assets/images/fontawesome/svgs/solid/chart-line.svg')
    },
    github () {
        return require('../assets/images/fontawesome/svgs/brands/github.svg')
    },
    file_alt () {
        return require('../assets/images/fontawesome/svgs/solid/file-alt.svg')
    },
    info_circle () {
        return require('../assets/images/fontawesome/svgs/solid/info-circle.svg')
    }
    */

    return require('./assets/images/fontawesome/svgs/solid/home.svg');
}

export {lookup_md_icon};