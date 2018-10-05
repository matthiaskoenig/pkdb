<template>
    <div id="output">
        <GetData :resource_url="resource_url">
            <div slot-scope="output">
                <div v-if="output.loaded">
                    <OutputDetail :output="output.data" :resource_url="resource_url" />
                </div>
            </div>
        </GetData>
    </div>
</template>

<script>
    import OutputDetail from '@/components/detail/OutputDetail'

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
                return this.$store.state.endpoints.api + '/outputs_read/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>