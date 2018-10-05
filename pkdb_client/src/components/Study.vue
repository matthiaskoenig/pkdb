<template>
    <div id="study">
        <GetData :resource_url="resource_url">
            <div slot-scope="study">
                <div v-if="study.loaded">
                    <StudyDetail :study="study.data" :resource_url="resource_url" />
                </div>
            </div>
        </GetData>
    </div>
</template>

<script>
    import StudyDetail from '@/components/detail/StudyDetail'

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