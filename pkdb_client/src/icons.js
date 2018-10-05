/**
 * Helpers to work with icons.
 */

const icons_table = {
    home: 'fas fa-home',
    studies: 'fas fa-procedures',
    study: 'fas fa-procedures',
    groups: 'fas fa-users',
    group: 'fas fa-users',
    individuals: 'fas fa-user',
    individual: 'fas fa-user',
    interventions: 'fas fa-capsules',
    intervention: 'fas fa-capsule',
    outputs: 'fas fa-chart-bar',
    output: 'fas fa-chart-bar',
    timecourses: 'fas fa-chart-line',
    timecourse: 'fas fa-chart-line',
    references: 'fas fa-file-alt',
    reference: 'fas fa-file-alt',
    about: 'fas fa-info-circle',
    api: 'fas fa-code',
    admin: 'fas fa-cogs',
    account: 'fas fa-user-circle',
    github: 'fab fa-github',
    files: 'fas fa-file-medical',
    file: 'fas fa-file-medical',
    substance: 'fas fa-tablets'
};

function lookup_icon(key){
    return icons_table[key]
}

export {lookup_icon};