import axios from 'axios'

let SearchMixin = {
    methods: {
        downloadData() {
            this.loadingDownload = true
            let headers = {};
            if (localStorage.getItem('token')) {
                headers = {Authorization: 'Token ' + localStorage.getItem('token')}
            }
            axios.get(this.search_url + "&download=true", {headers: headers, responseType: 'arraybuffer',})
                .then(response => {
                    let blob = new Blob([response.data], {type: 'application/zip'}),
                        url = window.URL.createObjectURL(blob)
                    window.open(url)
                })
                .catch(err => {
                    console.log(err.response.data);
                    this.loadingDownload = false
                })
                .finally(() => this.loadingDownload = false);
        }
    },
    computed: {
        url() {
            /** Calculates the search url based on current state in store.. */
            let url = this.$store.state.endpoints.api  + 'pkdata/?format=json'

            for (const [key, value] of Object.entries(this.$store.state.queries)) {
                if (value.length > 0) {

                    url = url + "&" + key + "=" + value.map(i => i.sid).join("__")
                }
            }
            for (const [key, value] of Object.entries(this.$store.state.queries_users)) {
                if (value.length > 0) {

                    url = url + "&" + key + "=" + value.map(i => i.username).join("__")
                }
            }
            for (const [key, value] of Object.entries(this.$store.state.subjects_queries)) {
                // handle groups

                if (this.$store.state.subjects_boolean.groups_query) {
                    if (value.length > 0) {
                        url = url + "&" + "groups__" + key + "=" + value.map(i => i.sid).join("__")
                    }
                } else {
                    url = url + "&" + "groups__" + key + "=0"
                }

                // handle individuals
                if (this.$store.state.subjects_boolean.individuals_query) {
                    if (value.length > 0) {
                        url = url + "&" + "individuals__" + key + "=" + value.map(i => i.sid).join("__")
                    }
                } else {
                    url = url + "&" + "individuals__" + key + "=0"
                }
            }
            if (! this.$store.state.queries_output_types.timecourse_query) {
                    url = url + "&" + "outputs__output_type__exclude=timecourse"
                }
            if (! this.$store.state.queries_output_types.output_query) {
                url = url + "&outputs__output_type__exclude=output&outputs__output_type__exclude=array"
            }
            return url
        },
    },
};

export {SearchMixin};