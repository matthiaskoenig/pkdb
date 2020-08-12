import axios from 'axios'
import {lookupIcon} from "@/icons"

let searchTableMixin = {
    data() {
        return {
            count: 0,
            entries: [],
            search: "",
            options: {},
            loading: false,
            footer_options:{
                itemsPerPageOptions:[5, 10, 20, 50, 100]
            },
            table_class: "elevation-1",
        }
    },
    props: {
        search_ids: {
            type: Boolean,
            default: false
        },
        ids: {
            type: Array,
            default: () => ["noIdSearch"]

        },
        autofocus: {
            type: Boolean,
            default: true
        },
        ntype: {
            type: String,
            default: () => "all"

        }



    },
    mounted() {
        this.getData()
    },
    watch: {
        pagination: {
            handler() {
                this.getData()
            },
            deep: true
        },
        search(){
                    this.getData();
                },
        ntype: {
            handler() {
                this.getData();
            },
            deep: true
        },
        url: {
            handler() {
                this.getData();
            },
            deep: true
        }
    },
    computed: {
        backend() {
            return this.$store.state.django_domain;
        },
        api() {
            return this.$store.state.endpoints.api;
        },
        resource_url() {

            return this.$store.state.endpoints.api  + this.otype + '/?format=json'
        },
        url() {

            var url = this.resource_url
            if(this.options.itemsPerPage) {
                url = url
                    + '&page=' + this.options.page
                    + '&page_size=' + this.options.itemsPerPage
                    //+ '&ordering=' + this.options.sortDesc + this.options.sortBy;
            }
            if (this.search) {
                url += '&search_multi_match=' + this.search
            }
            if (this.ntype !== "all" ){
                url += '&ntype=' + this.ntype
            }
            if (["outputs", "timecourses", "interventions"].includes(this.otype)) {
                url += '&normed=true'
            }
            if (this.search_ids) {
                url += '&ids=' + this.ids.join("__")
            }
            return url
        },
        descending() {
            return (this.options.sortDesc ? "-" : "");
        }
    },
    methods: {
        faIcon(key) {
            return lookupIcon(key)
        },
        searchUpdate(newValue) {
            this.search = newValue
        },
        get_ids(array_of_obj) {
            return array_of_obj.map(i => i.pk)
        },

        getData() {
            if (localStorage.getItem('token')) {
                var headers = {Authorization: 'Token ' + localStorage.getItem('token')}
            } else {
                headers = {}
            }
            axios.get(this.url, {headers: headers})
                .then(res => {
                    this.entries = res.data.data.data;
                    this.count = res.data.data.count;

                })
                .catch(err => {
                    console.log(err.response.data);
                })
                .finally(() => this.loading = false);
        },

    }
};

const UrlMixin = {
    methods: {
        group_url(pk) {
            return this.$store.state.endpoints.api + 'groups/' + pk + '/'
        },
        individual_url(pk) {
            return this.$store.state.endpoints.api + 'individuals/' + pk + '/'
        },
        output_url(pk) {
            return this.$store.state.endpoints.api + 'outputs/' + pk + '/'
        },
        timecourse_url(pk) {
            return this.$store.state.endpoints.api + 'timecourses/' + pk + '/'
        },
        timecourses_url(pks) {
            return this.$store.state.endpoints.api + 'timecourses/?ids=' + pks.join('__')
        },
        intervention_url(pk) {
            return this.$store.state.endpoints.api + 'interventions/' + pk + '/'
        },
        reference_url(pk) {
            return this.$store.state.endpoints.api + 'references/' + pk + '/'
        },
        characterica_url(ids) {
            return this.$store.state.endpoints.api + 'characteristica/?ids=' + ids.join('__')
        },
    }
};
export {searchTableMixin, UrlMixin}