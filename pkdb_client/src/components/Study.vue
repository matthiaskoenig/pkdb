<template>
    <span id="study">
        <get-data :resource_url="resource_url">
            <div slot-scope="study">
                <StudyDetail :study="study.data" :resource_url="resource_url" />
            </div>
        </get-data>
    </span>
</template>

<script>
    import StudyDetail from './detail/StudyDetail'

    export default {
        name: 'Study',
        components: {
            StudyDetail
        },
        computed: {
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var entry_id = tokens[tokens.length-1];
                return this.$store.state.endpoints.api + '/studies_read/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>