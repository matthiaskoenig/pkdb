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
            color="#1E90FF"
            hide-details
            :autofocus="autofocus"
    />
</v-toolbar>
</template>

<script>
    import {IconsMixin} from "../../icons";

    export default {
      mixins: [IconsMixin],
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