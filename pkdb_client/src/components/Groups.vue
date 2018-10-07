<!--
<template>
    <list-view :resource_url="resource_url">
        <template slot="listview">
            <groups-table :data="data" :resource_url="resource_url"/>
        </template>
    </list-view>
</template>

-->
<template>
    <get-paginated-data :resource_url="resource_url">
        <div slot-scope="data">
            <groups-table :data="data" :resource_url="resource_url" />
        </div>
    </get-paginated-data>
</template>


<script>
    import GetPaginatedData from './api/GetPaginatedData';
    import GroupsTable from "./tables/GroupsTable";
    // import ListView from "./ListView";

    export default {
        name: 'Groups',
        components: {
            GetPaginatedData: GetPaginatedData,
            GroupsTable: GroupsTable,

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
                return this.api + '/groups_read/?format=json';
            },
        }
    }
</script>

<style></style>
