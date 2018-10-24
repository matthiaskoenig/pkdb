<template>
    <span id="output">
        <get-data :resource_url="resource_url">
            <div slot-scope="output">
                <output-detail :output="output.data" :resource_url="resource_url" />
            </div>
        </get-data>
    </span>
</template>

<script>
    import OutputDetail from './detail/OutputDetail'

    export default {
        name: 'Output',
        components: {
            OutputDetail
        },
        computed: {
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var entry_id = tokens[tokens.length-1];
                return this.$store.state.endpoints.api + '/outputs_elastic/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>