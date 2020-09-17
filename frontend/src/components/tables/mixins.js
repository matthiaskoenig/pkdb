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
            exclude_abstract: false,
            footer_options:{
                itemsPerPageOptions: [5, 10, 20, 50, 100]
            },
            table_class: "elevation-0",
            windowHeight: window.innerHeight-260,

        }
    },
    props: {
        search_hash: {
            type: Boolean,
            default: false
        },
        hash: {
            type: String,
            default: () => "BoHash"

        },
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

        },
        ntypes: {
            type: Array,
            default: () => []
        },
        data_type: {
            type: String,
        }

    },
    mounted() {
        this.$nextTick(() => {
            window.addEventListener('resize', this.onResize);
        })
        this.getData()
    },

    beforeDestroy() {
        window.removeEventListener('resize', this.onResize);
    },
    watch: {

        search(){
            this.options.page = 1
            this.getData();
            this.$store.state.highlight = this.search
        },
        hash(){
            this.options.page = 1
            this.getData();
        },
        url: {
            handler() {
                this.getData();
            },
            deep: true
        }
    },
    computed: {
        highlight(){
            return this.$store.state.highlight
        },
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
            let url = this.resource_url
            if(this.options.itemsPerPage) {
                url = url
                    + '&page=' + this.options.page
                    + '&page_size=' + this.options.itemsPerPage
                    //+ '&ordering=' + this.options.sortDesc + this.options.sortBy;
            }
            if(this.exclude_abstract){
                url += '&dtype__exclude=abstract'

            }
            if (this.search) {
                url += '&search_multi_match=' + this.search
            }
            if (this.ntype !== "all" ){
                url += '&ntype=' + this.ntype
            }
            if (this.ntypes.length > 0 ){
                url += '&ntype__in=' + this.ntypes.join("__")
            }
            if (["outputs", "interventions"].includes(this.otype)) {
                url += '&normed=true'
            }
            if (this.search_ids) {
                url += '&ids=' + this.ids.join("__")
            }
            if (this.data_type) {
                url += '&data_type=' + this.data_type
            }
            if (this.search_hash) {
                url += '&hash=' + this.hash
            }
            return url
        },
        descending() {
            return (this.options.sortDesc ? "-" : "");
        }
    },
    methods: {
        onResize() {
            this.windowHeight = window.innerHeight-260
        },
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
            let headers = {};
            if (localStorage.getItem('token')) {
                headers = {Authorization: 'Token ' + localStorage.getItem('token')}
            }
            axios.get(this.url, {headers: headers})
                .then(response => {
                    this.entries = response.data.data.data;
                    this.count = response.data.data.count;
                })
                .catch(err => {
                    console.log(this.url);
                    console.log(err);
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