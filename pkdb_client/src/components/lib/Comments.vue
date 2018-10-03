<template>
    <div id="comments">
        <md-chip v-for="comment in comments" :key="comment">
            <UserAvatar :user="comment.user"></UserAvatar>
            {{ comment.text }}
        </md-chip>
    </div>
</template>

<script>
    export default {
        name: "Comments",
        props: {
            comments: {
                type: Object,
            }
        }
    }
</script>

<style scoped>

</style>