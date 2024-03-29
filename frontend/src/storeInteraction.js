let StoreInteractionMixin = {
    methods: {
        reset() {
            this.$store.commit('resetQuery');
        },
        updateSearch(study_info) {
            let study = {
                "query_type": "queries",
                "key": "studies__sid__in",
                "value": [study_info]}
            this.update_store(study)
            this.concise = false
        },
        update_store(q) {
            this.$store.dispatch('updateQueryAction', {
                query_type: q.query_type,
                key: q.key,
                value: q.value,
            })
        }
    },
    computed: {
        mini:  {
            get() {
                return !this.$store.state.display_detail
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "display_detail",
                    value: !value,
                })
            }
        },
        results: {
            get(){
                return this.$store.state.results
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "results",
                    value: value,
                })
            }
        },
        loadingDownload: {
            get(){
                return this.$store.state.loadingDownload
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "loadingDownload",
                    value: value,
                })
            }
        },
        cancelSource: {
            get(){
                return this.$store.state.cancelSource
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "cancelSource",
                    value: value,
                })
            }
        },
        data_info_type() {
            /** Type of information to display */
            return this.$store.state.data_info_type
        },
        data_info() {
            /** actual information to display */
            return this.$store.state.data_info
        },
        individuals_query: {
            get(){
                return this.$store.state.subjects_boolean.individuals_query
            },
            set (value) {
                this.$store.dispatch('updateQueryAction', {
                    query_type: "subjects_boolean",
                    key: "individuals_query",
                    value: value,      })
            }
        },
        groups_query: {
            get(){
                return this.$store.state.subjects_boolean.groups_query
            },
            set (value) {
                this.$store.dispatch('updateQueryAction', {
                    query_type: "subjects_boolean",
                    key: "groups_query",
                    value: value,      })
            },
        },
        concise: {
            get(){
                return this.$store.state.concise
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "concise",
                    value: value,
                })
            }
        },
        display_detail: {
            get() {
                return this.$store.state.display_detail
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "display_detail",
                    value: value,
                })
            }
        },
        hide_search:  {
            get() {
                return this.$store.state.hide_search
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "hide_search",
                    value: value,
                })
            }
        },
        highlight:  {
            get() {
                return this.$store.state.highlight
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "highlight",
                    value: value,
                })
            }
        },
        detail_info: {
            get() {
                return this.$store.state.detail_info
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "detail_info",
                    value: value,
                })
            }
        },
        show_type: {
            get() {
                return this.$store.state.show_type
            },
            set(value) {
                this.$store.dispatch('updateAction', {
                    key: "show_type",
                    value: value,
                })
            }
        }
    }
}
export {StoreInteractionMixin}