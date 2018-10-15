<template>
    <!--
    <get-paginated-data :resource_url="resource_url">
        <div slot-scope="data">
            <studies-table :data="data" :resource_url="resource_url" />
        </div>
    </get-paginated-data>
    -->
    <studies-table2></studies-table2>

</template>

<script>
    import StudiesTable2 from "./tables/StudiesTable2";


    export default {
        name: 'References',
        components: {
            StudiesTable2: StudiesTable2,

        },
        methods: {},
        data() {
            return {
            }
        },
        computed: { // vuex store
            api() {
                return this.$store.state.endpoints.api;
            },
            resource_url() {
                return this.api + '/studies_read/?format=json';
            },
        }
    }
</script>

<style></style>