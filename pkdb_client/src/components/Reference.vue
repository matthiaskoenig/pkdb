<template>
    <div id="reference">
        <GetData :resource_url="resource_url">
            <div slot-scope="reference">
                <div v-if="reference.loaded">
                    <ReferenceDetail :reference="reference.data" :resource_url="resource_url" />
                </div>
            </div>
        </GetData>
    </div>
</template>

<script>
    import ReferenceDetail from '@/components/detail/ReferenceDetail'

    export default {
        name: 'Reference',
        components: {
            ReferenceDetail
        },
        computed: {
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var entry_id = tokens[tokens.length-1];
                return this.$store.state.endpoints.api + '/references_read/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>