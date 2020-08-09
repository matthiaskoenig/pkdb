<template>
    <div id="group-detail">
        <get-data :resource_url="resource_url">
            <div slot-scope="info_node">
              {{info_node.data}}
            </div>
        </get-data>
    </div>
</template>

<script>

    export default {
        name: 'Individual',
        components: {

        },
        computed: {
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var entry_id = tokens[tokens.length-1];
                return this.$store.state.endpoints.api + 'info_nodes/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>