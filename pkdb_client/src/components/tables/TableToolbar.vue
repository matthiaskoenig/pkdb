<template>
<v-toolbar id="heading-toolbar" color="primary" dark>
    <heading :count="count"
             :icon="icon(otype)"
             :title="capitalizeFirstLetter(otype)"
             :resource_url="url"
    />
    <v-spacer />
    <v-text-field
            v-model="search"
            append-icon="fa-search"
            label="Search"
            single-line
            hide-details
            :autofocus="autofocus"
    />
</v-toolbar>
</template>

<script>
    import {lookup_icon} from "@/icons"

    export default {
        name: "TableToolbar",
        data () {
            return {
                search: '',
            }
        },
        props: {
            otype: {
                type: String,
                required: true
            },
            count: {
                type: Number,
            },
            url: {
                type: String
            },
            autofocus: {
                type: Boolean,
                default: false
            }
        },
        methods: {
            icon(key) {
                return lookup_icon(key)
            },
            capitalizeFirstLetter(string) {
                return string.charAt(0).toUpperCase() + string.slice(1);
            },
        },
        watch: {
            search: function(newVal, oldVal) {
                // console.log("search:" + this.search);
                this.$emit('update', newVal)
            }
        }
    }
</script>

<style scoped>

</style>