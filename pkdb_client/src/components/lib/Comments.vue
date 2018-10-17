<template>
    <div id="comments" v-if="comments && comments.length>0">
        <span class="attr">Comments</span><br/>
        <span v-for="item in comments" :key="item.pk">
            <user-avatar :user="comment.user"></user-avatar>
            {{ comment.text }}<br />
        </span>

    </div>
</template>

<script>
    export default {
        name: "Comments",
        props: {
            comments: {
                type: Array,
            }
        }
    }
</script>

<style scoped>

</style>