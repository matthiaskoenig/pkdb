<template>
    <div id="group-detail">
        <GetData :resource_url="resource_url">
            <div slot-scope="group">
                <div v-if="group.loaded">
                    <GroupDetail :group="group.data" :resource_url="resource_url" />
                </div>
            </div>
        </GetData>
    </div>
</template>

<script>
    import GroupDetail from '@/components/detail/GroupDetail'

    export default {
        name: 'Groups',
        components: {
            GroupDetail: GroupDetail
        },
        computed: {
            resource_url() {
                var path = this.$route.path;
                console.log(path);
                console.log(typeof path);
                var matches = path.match('groups\/(\d+)');
                console.log(matches);

                var group_id = 1; // matches[1]
                return this.$store.state.endpoints.api + '/groups_read/'+ group_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>