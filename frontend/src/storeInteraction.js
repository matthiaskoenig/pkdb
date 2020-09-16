let StoreInteractionMixin = {
    methods: {
        reset() {
            this.$store.commit('resetQuery');
        },
    },
    computed: {
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