<template>
    <GetData :resource_url="resource_url">
        <div slot-scope="resource">
            <GroupsTable :resource="resource" :api="api"/>
        </div>
    </GetData>

</template>
<script>

    import GetData from '@/components/api/GetPaginatedData';
    import GroupsTable from "@/components/tables/GroupsTable";

    export default {
        name: 'Groups',
        components: {
            GetData: GetData,
            GroupsTable: GroupsTable,

        },
        props: {
            api: String
        },
        methods: {},
        data() {
            return {
                resource_url: this.api + '/groups_read/?format=json',
            }
        }
    }
</script>
<style>
</style>