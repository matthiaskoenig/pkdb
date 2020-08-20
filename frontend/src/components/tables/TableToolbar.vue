<template>
<v-toolbar id="heading-toolbar" dense flat>
    <heading :count="count"
             :icon="faIcon(otype)"
             :title="capitalizeFirstLetter(otype)"
             :resource_url="url"
    />
    <v-spacer />
    <v-text-field
            v-model="search"
            append-icon="fa-search"
            label="Search table"
            single-line
            color="white"
            hide-details
            :autofocus="autofocus"
    />
</v-toolbar>
</template>

<script>
    import {lookupIcon} from "@/icons"

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
                default: true
            }
        },
        methods: {
            faIcon(key) {
                return lookupIcon(key)
            },
            capitalizeFirstLetter(string) {
                return string.charAt(0).toUpperCase() + string.slice(1);
            },
        },
        watch: {
            search: function(newVal) {
                this.$emit('update', newVal)
            }
        }
    }
</script>

<style scoped>

</style>