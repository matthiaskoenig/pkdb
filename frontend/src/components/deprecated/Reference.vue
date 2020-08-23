<template>
    <span id="reference">
        <get-data :resource_url="resource_url">
            <div slot-scope="reference">
                <reference-detail :reference="reference.data" :resource_url="resource_url" />
            </div>
        </get-data>
    </span>
</template>

<script>
    import ReferenceDetail from '../detail/ReferenceDetail'

    export default {
        name: 'Reference',
        components: {
            ReferenceDetail
        },
        computed: {
            resource_url() {
                const path = this.$route.path;
                const tokens = path.split('/');
                const entry_id = tokens[tokens.length - 1];
                console.log(entry_id);
                return this.$store.state.endpoints.api + 'references/'+ entry_id + '/';
            }
        },
    }
</script>
<style>
</style>