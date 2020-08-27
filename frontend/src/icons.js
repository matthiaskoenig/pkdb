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
    intervention: 'fas fa-capsules',
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
    files: 'fas fa-file',
    file: 'fas fa-file',
    file_excel: 'fas fa-file-excel',
    file_image: 'fas fa-file-image',
    file_csv: 'fas fa-file-csv',
    file_pdf: 'fas fa-file-pdf',
    substance: 'fas fa-tablets',
    substances: 'fas fa-tablets',
    characteristicas: 'fas fa-ticket-alt',
    characteristica: 'fas fa-ticket-alt',
    curation: 'fas fa-book-reader',
    data: 'fas fa-database',
    previous: 'fas fa-arrow-left',
    next: 'fas fa-arrow-right',
    star: 'fas fa fa-star',
    warning: 'fas fa-exclamation-triangle',
    private: 'fas fa-lock',
    public: 'fas fa-lock-open',
    closed: 'fab fa-creative-commons-pd',
    open: 'fab fa-creative-commons-pd-alt',
    na: 'fas fa-ban',
    delete: 'fas fa-times-circle',
    success: 'fas fa-check-circle',
    measurement_type: 'fas fa-heartbeat',
    measurement_types: 'fas fa-heartbeat',
    tissue: 'fas fa-map-marker-alt',
    tissues: 'fas fa-map-marker-alt',
    search: 'fas fa-search',
    info: 'fas fa-info-circle',
    plus: 'fas fa-plus',
    minus: 'fas fa-minus',
    download: 'fas fa-file-download',
    left_arrow: 'fas fa-arrow-left',
    right_arrow: 'fas fa-arrow-right',

};

/**
 * Lookup icon key or return font awesome icon directly.
 */
function lookupIcon(key) {
    if (key.startsWith("fa")){
        return key
    } else {
        return icons_table[key]
    }
}

let IconsMixin = {
    methods: {
        faIcon: function (key) {
            return lookupIcon(key)
        },
    },
};

export {lookupIcon, IconsMixin};