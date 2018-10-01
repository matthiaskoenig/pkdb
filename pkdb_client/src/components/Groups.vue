<template>
    <GetData :resource_url="resource_url" >
        <div slot-scope="resource">
            <GroupsTable :resource="resource" :api="api" />
        </div>
    </GetData>

</template>
<script>

    import GroupsTable from "./GroupsTable";
    import {id_from_url} from "./utils";
    import GetData from './GetPaginatedData';

    export default {
    name: 'Groups',
    components: {
        GetData: GetData,
        GroupsTable:GroupsTable,

    },
    props: {
        api: String
    },
    methods:{

        id_from_url(url){
            return id_from_url(url);
        }
    },
    data() {
        return {
            resource_url: this.api + '/groups_read/?format=json',
        }
        }
}
</script>
<style>
</style>