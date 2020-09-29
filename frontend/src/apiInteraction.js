import axios from 'axios'
import {StoreInteractionMixin} from "./storeInteraction";

let ApiInteractionMixin = {
    mixins: [StoreInteractionMixin],
    computed: {
        api() {
            return this.$store.state.endpoints.api;
        },
        api_swagger() {
            return this.$store.state.endpoints.api_swagger;
        },
        api_redoc() {
            return this.$store.state.endpoints.api_redoc;
        },
        username(){
            return this.$store.state.username
        }
    },
    methods: {
        getStudy(sid, update_search=false) {
            // object is an InfoNode
            let url = `${this.$store.state.endpoints.api}studies/${sid}/?format=json`;
            let headers = {};
            if (localStorage.getItem('token')) {
                headers = {Authorization: 'Token ' + localStorage.getItem('token')}
            }
            // get data (FIXME: caching of InfoNodes in store)
            axios.get(url, {headers: headers})
                .then(response => {
                    if (response.data.sid) {
                        if(update_search){
                            this.updateSearch(response.data)
                        }
                        this.show_type = "study";
                        this.detail_info = response.data;
                        this.display_detail = true;
                    } else {
                        this.$route.push('/404')
                    }
                })
                .catch(err => {
                    this.exists = false;
                    this.$router.push('/404')
                    console.log(err)
                })
                .finally(() => this.loading = false);


        },
        getInfo(pk, show_type) {
            // object is an InfoNode
            let url = `${this.$store.state.endpoints.api}${show_type}s/${pk}/?format=json`;

            // get data (FIXME: caching of InfoNodes in store)
            axios.get(url)
                .then(response => {
                    this.show_type = show_type;
                    this.detail_info =  response.data;
                    this.display_detail = true;
                })
                .catch(err => {
                    this.exists = false;
                    console.log(err)
                })
                .finally(() => this.loading = false);

        },
        fetch_data(url) {
            let headers = {};
            if (localStorage.getItem('token')) {
                headers = {Authorization: 'Token ' + localStorage.getItem('token')}
            }
            // get data (FIXME: caching of InfoNodes in store)
            axios.get(url, {headers: headers})
                .then(response => {
                    this.data = response.data;
                })
                .catch((error) => {
                    this.data = null;
                    console.error(url);
                    console.error(error);
                })

        }

    }
}
export {ApiInteractionMixin}