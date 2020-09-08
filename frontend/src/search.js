import axios from 'axios'

let SearchMixin = {
    methods: {
        downloadData() {
            this.loadingDownload = true
            let headers = {};
            if (localStorage.getItem('token')) {
                headers = {Authorization: 'Token ' + localStorage.getItem('token')}
            }
            axios.get(this.url + "&download=true", {headers: headers, responseType: 'arraybuffer',})
                .then(response => {
                    const a_ = document.createElement("a");
                    a_.href = URL.createObjectURL(new Blob([response.data], {type: 'application/x-zip-compressed'}))
                    a_.setAttribute("download", "pkdb_data.zip");
                    document.body.appendChild(a_);
                    a_.click();
                    document.body.removeChild(a_);
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

            var output_type__in = new Set(["output", "timecourse", "array"]);
            var filter_output_type = false

            var licence__in = new Set(["closed", "open"]);
            var filter_licence = false

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
                filter_output_type =true
                output_type__in.delete("timecourse")
                }
            if (! this.$store.state.queries_output_types.scatter_query) {
                filter_output_type = true
                output_type__in.delete("array")
            }
            if (! this.$store.state.queries_output_types.output_query) {
                filter_output_type =true
                output_type__in.delete("output")

            }
            if(filter_output_type) {
                if ([...output_type__in].length === 0) {
                    url = url + "&" + "outputs__output_type__in=0"
                } else {
                    url = url + "&" + "outputs__output_type__in=" + [...output_type__in].join("__")
                }
            }

            if (! this.$store.state.licence_boolean.open) {
                filter_licence =true
                licence__in.delete("open")
            }
            if (! this.$store.state.licence_boolean.closed) {
                filter_licence = true
                licence__in.delete("closed")
            }

            if(filter_licence) {
                if ([...licence__in].length === 0) {
                    url = url + "&" + "licence__in=0"
                } else {
                    url = url + "&" + "studies__licence__in=" + [...licence__in].join("__")
                }
            }
            return url
        },
    },
};

export {SearchMixin};