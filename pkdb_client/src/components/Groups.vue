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
    <!--

    <get-paginated-data :resource_url="resource_url">
        <div slot-scope="data">
            <groups-table :data="data" :resource_url="resource_url" />
        </div>
    </get-paginated-data>
    -->
    <groups-table2/>
</template>


<script>
    import GroupsTable2 from "./tables/GroupsTable2";

    export default {
        name: 'Groups',
        components: {
            GroupsTable2: GroupsTable2,

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
