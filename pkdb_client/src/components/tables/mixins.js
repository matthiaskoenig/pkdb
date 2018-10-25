
import axios from 'axios'
import {lookup_icon} from "@/icons"

var searchTableMixin = {
    data () {
        return {
            count: 0,
            entries: [],
            search:"",
            loading: true,
            pagination: {},
            rowsPerPageItems: [5, 10, 20, 50, 100],
            table_class: "elevation-1",
        }
    },
    props:{
            ids:{
                type: Array,
                default: () => []

            },

        },
    mounted () {
        this.getData()
    },
    watch: {
        pagination: {
            handler () {
                this.getData()
            },
            deep: true
        },
        search: {
            handler () {
                this.getData();
            },
            deep: true
        }
    },
    computed: {
        backend(){
            return this.$store.state.django_domain;
        },
        api(){
            return this.$store.state.endpoints.api;
        },
        resource_url() {
            return this.$store.state.endpoints.api  + '/' + this.otype + '_elastic/?format=json'
        },
        url() {
            let url = this.resource_url
                + '&page='+ this.pagination.page
                + '&page_size='+ this.pagination.rowsPerPage
                + '&ordering='+ this.descending+ this.pagination.sortBy;
            if(this.search){
                url += '&search='+ this.search
            }
            if(this.ids.length > 0){
                url += '&ids=' + this.ids.join("__")

            }
            return url
        },
        descending() {
            return (this.pagination.descending ? "-" : "");
        }
    },
    methods: {
        icon(key) {
            return lookup_icon(key)
        },
        searchUpdate (newValue) {
            this.search = newValue
        },
        get_ids(array_of_obj) {
            return array_of_obj.map(i => i.pk)
        },

        getData() {
            axios.get(this.url)
                .then(res => {
                    this.entries = res.data.data.data;
                    this.count = res.data.data.count;
                })
                .catch(err => console.log(err.response.data))
                .finally(() => this.loading = false);
        },

    }
};

var UrlMixin = {
    methods: {group_url(pk) {
            return this.$store.state.endpoints.api  + '/groups_elastic/'+ pk +'/'


        },
        individual_url(pk) {
            return this.$store.state.endpoints.api  + '/individuals_elastic/'+ pk +'/'


        },
        intervention_url(pk) {
            return this.$store.state.endpoints.api  + '/interventions_elastic/'+ pk +'/'


        },
        reference_url(pk) {
            return this.$store.state.endpoints.api  + '/references_elastic/'+ pk +'/'


        },
        characterica_url(ids) {
            return this.$store.state.endpoints.api + '/characteristica_elastic/?get_ids=' + ids.join('__')
        },}
};
export {searchTableMixin,UrlMixin}